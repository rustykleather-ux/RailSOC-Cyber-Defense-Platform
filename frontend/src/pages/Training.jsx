import DemoControls from "../components/DemoControls";

function Training({ simulateAttack, resetDemo }) {
  return (
    <DemoControls
      simulateAttack={simulateAttack}
      resetDemo={resetDemo}
    />
  );
}

export default Training;