import { useState } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import MapCont from "./components/MapContainer";
import AuthProvider from "./Auth";
import "./App.css";

function App() {
  const [sidebarActive, setSidebarActive] = useState(false);
  const [activeRole, setActiveRole] = useState("policia");
  const [routeInfo, setRouteInfo] = useState(null);

  const toggleSidebar = () => {
    setSidebarActive(!sidebarActive);
  };

  const handleRoleChange = (role) => {
    setActiveRole(role);
  };

  return (
    <AuthProvider>
      <div className="app">
        <Header
          activeRole={activeRole}
          onRoleChange={handleRoleChange}
          sidebarActive={sidebarActive}
          toggleSidebar={toggleSidebar}
        />
        <div className="container">
          <Sidebar
            routeInfo={routeInfo}
            setRouteInfo={setRouteInfo}
            active={sidebarActive}
          />
          <MapCont
            marginLeft={sidebarActive ? "300px" : "0"}
            activeRole={activeRole}
            routeInfo={routeInfo}
            setRouteInfo={setRouteInfo}
          />
        </div>
      </div>
    </AuthProvider>
  );
}

export default App;
