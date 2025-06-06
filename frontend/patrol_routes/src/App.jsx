import { useState } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import MapCont from "./components/MapContainer";
import AuthProvider from "./Auth";
import NotificationProvider from "./components/NotificationProvider";
import "./App.css";

function App() {
  const [sidebarActive, setSidebarActive] = useState(false);
  const [selCai, setSelCai] = useState(0);
  const [activeRole, setActiveRole] = useState("policia");
  const [routeInfo, setRouteInfo] = useState(null);

  const toggleSidebar = () => {
    setSidebarActive(!sidebarActive);
  };

  const handleRoleChange = (role) => {
    setActiveRole(role);
  };

  return (
    <NotificationProvider>
      <AuthProvider>
        <div className="app">
          <Header
            activeRole={activeRole}
            onRoleChange={handleRoleChange}
            sidebarActive={sidebarActive}
            selCai={selCai}
            setSelCai={setSelCai}
            toggleSidebar={toggleSidebar}
          />
          <div className="container">
            <Sidebar
              routeInfo={routeInfo}
              setRouteInfo={setRouteInfo}
              selCai={selCai}
              setSelCai={setSelCai}
              active={sidebarActive}
            />
            <MapCont
              marginLeft={sidebarActive ? "300px" : "0"}
              activeRole={activeRole}
              routeInfo={routeInfo}
              setRouteInfo={setRouteInfo}
              selCai={selCai}
            />
          </div>
        </div>
      </AuthProvider>
    </NotificationProvider>
  );
}

export default App;
