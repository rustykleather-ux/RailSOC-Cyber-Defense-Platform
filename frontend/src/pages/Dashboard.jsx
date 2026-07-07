import EnvironmentOverview from "../components/EnvironmentOverview";
import RailroadMap from "../components/RailroadMap";

function Dashboard({ dashboard, alerts, incidents, vulnerabilities, devices }) {
  return (
    <>
      <EnvironmentOverview
        dashboard={dashboard}
        alerts={alerts}
        incidents={incidents}
        vulnerabilities={vulnerabilities}
      />

      <RailroadMap devices={devices} />
    </>
  );
}

export default Dashboard;