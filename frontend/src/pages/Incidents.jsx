import IncidentCenter from "../components/IncidentCenter";

function Incidents({
  incidents,
  acknowledgeIncident,
  assignIncident,
  updateIncidentNotes,
  closeIncident,
}) {
  return (
    <IncidentCenter
      incidents={incidents}
      acknowledgeIncident={acknowledgeIncident}
      assignIncident={assignIncident}
      updateIncidentNotes={updateIncidentNotes}
      closeIncident={closeIncident}
    />
  );
}

export default Incidents;