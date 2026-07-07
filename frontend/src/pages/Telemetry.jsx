import LivePlantStatus from "../components/LivePlantStatus";

function Telemetry({ plantStatus }) {
  return <LivePlantStatus plantStatus={plantStatus} />;
}

export default Telemetry;