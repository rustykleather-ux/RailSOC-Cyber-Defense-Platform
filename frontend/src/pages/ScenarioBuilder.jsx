import Training from "./Training";
import CreateScenario from "./CreateScenario";

function ScenarioBuilder({
  simulateAttack,
  resetDemo,
  onScenarioComplete,
}) {
  return (
    <div className="scenario-builder-page">
      <div className="page-heading">
        <div>
          <p className="page-eyebrow">
            OT Security Exercises
          </p>

          <h1>Scenario Builder</h1>

          <p>
            Launch preset railroad cyber exercises or build
            custom attack scenarios against selected OT assets.
          </p>
        </div>
      </div>

      <section className="scenario-builder-section">
        <div className="section-heading">
          <h2>Preset Attack Library</h2>

          <p>
            Run predefined attack simulations against the
            TrackSentinel demonstration environment.
          </p>
        </div>

        <Training
          simulateAttack={simulateAttack}
          resetDemo={resetDemo}
        />
      </section>

      <section className="scenario-builder-section">
        <div className="section-heading">
          <h2>Custom Scenario</h2>

          <p>
            Select an attack, choose railroad assets, and
            execute a customized security exercise.
          </p>
        </div>

        <CreateScenario
          onScenarioComplete={onScenarioComplete}
        />
      </section>
    </div>
  );
}

export default ScenarioBuilder;