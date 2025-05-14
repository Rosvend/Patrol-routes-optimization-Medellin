from RoutePlanner.default_router import PoliceRouter, ORS_PROFILES, DEFAULT_ORS_PROFILE
from RoutePlanner.evaluate import evaluate_routes
from RoutePlanner.prediction.simple_wrapper import SimpleModelWrapper
from database.models import init_db, Manager, Route as DBRoute
from flasgger import Swagger, swag_from
from flask import Flask, request, current_app
from flask_cors import CORS
from flask_restful import Resource, Api
from flask_restful.reqparse import RequestParser
from logging.config import dictConfig
from markupsafe import escape
from werkzeug.security import check_password_hash as check_pw
from werkzeug.middleware.proxy_fix import ProxyFix
import datetime
import flask_login
import json
import jwt
import os
import yaml

TOKEN_EXPIRE_MINUTES = 30
ALGORITHM = "HS256"

login_manager = flask_login.LoginManager()

@login_manager.request_loader
def request_loader(request):
    if request.authorization is None:
        return None
    try:
        payload = jwt.decode(request.authorization.token,
                             current_app.secret_key,
                             algorithms=[ALGORITHM])
        return Manager.get(Manager.cedula == payload.get("sub"))
    except:
        return None

class RouteSuggestions(Resource):
    route_computer: PoliceRouter
    parser: RequestParser
    def __init__(self):
        self.route_computer = current_app.config['POLICE_ROUTER']
        self.parser = RequestParser()
        self.parser.add_argument('cai',
                                 required=True,
                                 type=int,
                                 location='args')
        self.parser.add_argument('n',
                                 type=int,
                                 location='args')
        self.parser.add_argument('profile',
                                 type=str,
                                 choices=ORS_PROFILES,
                                 location='args')
        self.parser.add_argument('exclude_station',
                                 type=bool,
                                 location='args')
        self.parser.add_argument('threshold',
                                 type=float,
                                 location='args')
        self.parser.add_argument('hotspots',
                                 type=bool,
                                 location='args')
        self.parser.add_argument('requested_spots',
                                 type=str,
                                 location='args')
    
    @swag_from("doc/RouteSuggestions_get.yml")
    def get(self):
        args = self.parser.parse_args()
        requested_spots = json.loads(args['requested_spots']) \
            if args['requested_spots'] is not None \
            else []
        result = self.route_computer.compute_routes(
            args['cai'],
            args['n'] if args['n'] is not None else 1,
            args['profile'] if args['profile'] is not None
                else DEFAULT_ORS_PROFILE,
            args['exclude_station'] is None,
            args['threshold'] if args['threshold'] is not None
                else 0.0,
            args['hotspots'] is not None,
            requested_spots)
        current_app.logger.info("Score for the routes: %7.2f", evaluate_routes(result))
        return result

class Route(Resource):
    @staticmethod
    def _get_route(date, cai_id, assigned_to):
        return DBRoute\
            .select()\
            .where((DBRoute.date == date)
               & (DBRoute.cai_id == cai_id)
               & (DBRoute.assigned_to == assigned_to))\
            .first()
    
    @swag_from("doc/Route_get.yml")
    def get(self, date, cai_id, assigned_to):
        try:
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return {"error": "Value %s is not of the YYYY-MM-DD date format." % date}, 400
        route = self._get_route(date, cai_id, assigned_to)
        if route == None:
            return {"error": "Route not found"}, 404
        return route.geometry

    @flask_login.login_required
    @swag_from("doc/Route_put.yml")
    def put(self, date, cai_id, assigned_to):
        if cai_id != flask_login.current_user.cai_id:
            return {"error": "Current manager is unauthorized to assign routes for %d." % cai_id}, 401
        route = request.get_json()
        route_id = (DBRoute
                        .insert(
                            geometry=route,
                            date=date,
                            cai_id=cai_id,
                            assigned_to=assigned_to,
                            assigned_by=flask_login.current_user
                        )
                        .on_conflict(
                            conflict_target=[DBRoute.date,
                                             DBRoute.cai_id,
                                             DBRoute.assigned_to],
                            preserve=[DBRoute.geometry],
                        )
                        .execute())
        return {"info": "route stored successfully."}

class Routes(Resource):
    @staticmethod
    def _get_routes(date, cai_id):
        return DBRoute\
            .select()\
            .where((DBRoute.date == date)
               & (DBRoute.cai_id == cai_id))

    @swag_from("doc/Routes_get.yml")
    def get(self, date, cai_id):
        try:
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return {"error": "Value %s is not of the YYYY-MM-DD date format." % date}, 400
        routes = self._get_routes(date, cai_id)
        if len(routes) == 0:
            return {"error": "No routes found for given date."}, 404
        return [route.toDict() for route in routes]
        

@swag_from("doc/login.yml")
def admin_login():
    # Use 'username' here for Oauth2 compliance
    cedula = request.form['username']
    password = request.form['password']

    try:
        manager = Manager.get(Manager.cedula == cedula)
    except Manager.DoesNotExist:
        return {"error": "Wrong credentials"}, 401
    if check_pw(manager.password_hash, password):
        expires_at = datetime.datetime.now(datetime.timezone.utc) \
            + datetime.timedelta(minutes=TOKEN_EXPIRE_MINUTES)
        token = jwt.encode({"sub": manager.cedula, "exp": expires_at},
                           current_app.secret_key,
                           algorithm=ALGORITHM)
        return {
            'access_token': token,
            'token_type': "bearer",
            'user': manager.toDict()
        }
    else:
        return {"error": "Wrong credentials"}, 401

def create_app(config_filename='config_dev.py'):
    __version__ = "0.0.2"

    app = Flask(__name__)
    CORS(app)
    api = Api(app)
    # app.config.from_prefixed_env(prefix="APP_")

    # Source the app config according to the environment
    if os.getenv("ENVIRONMENT") == "PRODUCTION":
        app.config.from_pyfile("config.py")
        # Tell the app it is behind one proxy
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )
    else:
        app.config.from_pyfile(config_filename)
    
    # Logging configuration optional
    try:
        dictConfig(app.config["LOGGING_CONFIG"])
    except KeyError:
        pass
        
    # Embed the router in the app itself (so it isn't re-created on
    # every request)
    app.config['POLICE_ROUTER'] = PoliceRouter(
        ors_key=app.config['ORS_KEY'],
        model_wrapper=SimpleModelWrapper(
            app.config['MODEL_PATH']
        )
    )

    # Source swagger endpoint documentation
    with open('doc/global.yml') as stream:
        doc_template = yaml.safe_load(stream)
    swagger = Swagger(app, template=doc_template)

    # Database initialization
    init_db(app, Manager, DBRoute)

    login_manager.init_app(app)
    
    # Register endpoints
    api.add_resource(Route,
        '/api/routes/<string:date>/<int:cai_id>/<int:assigned_to>')
    api.add_resource(Routes, '/api/routes/<string:date>/<int:cai_id>')
    api.add_resource(RouteSuggestions, '/api/routes')
    app.add_url_rule('/api/admin/login', methods=["POST"], view_func=admin_login)

    return app
