import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CircleGauge,
  Command,
  ListRestart,
  Route,
  ShieldCheck,
  TrainFront,
  TriangleAlert,
} from "lucide-react";
import RailroadMap from "../components/Railroadmap";
import {
  cancelDispatchCommand,
  clearRestriction,
  getDispatchWorkspace,
  retryDispatchCommand,
  submitDispatchCommand,
  submitDispatchRoute,
  submitRecoveryAction,
  submitRestriction,
} from "../services/dispatchService";
import "./DispatcherOperations.css";

const COMMAND_OPTIONS = {
  TRACK_BLOCK: [
    ["SET_SIGNAL", "Clear"],
    ["SET_SIGNAL", "Approach"],
    ["SET_SIGNAL", "Stop"],
  ],
  TRACK_SWITCH: [
    ["MOVE_SWITCH", "Normal"],
    ["MOVE_SWITCH", "Reverse"],
  ],
  TRAIN: [
    ["HOLD_TRAIN", "Held"],
    ["RELEASE_TRAIN", "Released"],
    ["APPLY_SPEED_RESTRICTION", "15"],
    ["REMOVE_SPEED_RESTRICTION", "Removed"],
  ],
  GRADE_CROSSING: [["ACTIVATE_CROSSING_SAFE_MODE", "Safe"]],
  OT_DEVICE: [
    ["ISOLATE_DEVICE", "Isolated"],
    ["RESTORE_DEVICE", "Online"],
    ["TRANSFER_TO_BACKUP", "Backup"],
  ],
};

function targetCollections(map) {
  return {
    TRACK_BLOCK: map?.blocks || [],
    TRACK_SWITCH: map?.switches || [],
    TRAIN: map?.trains || [],
    GRADE_CROSSING: map?.crossings || [],
    OT_DEVICE: map?.devices || [],
  };
}

export default function DispatcherOperations() {
  const [workspace, setWorkspace] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [targetType, setTargetType] = useState("TRACK_BLOCK");
  const [targetId, setTargetId] = useState("");
  const [commandChoice, setCommandChoice] = useState("SET_SIGNAL|Stop");
  const [routeForm, setRouteForm] = useState({
    train_id: "", start_block_id: "", destination_block_id: "",
  });
  const [restrictionReason, setRestrictionReason] = useState("");

  const load = useCallback(async () => {
    try {
      setWorkspace(await getDispatchWorkspace());
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 3000);
    return () => window.clearInterval(timer);
  }, [load]);

  const collections = useMemo(
    () => targetCollections(workspace?.map), [workspace?.map],
  );
  const options = COMMAND_OPTIONS[targetType];

  async function act(request) {
    setBusy(true);
    try {
      await request();
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  function changeTargetType(value) {
    setTargetType(value);
    setTargetId("");
    setCommandChoice(COMMAND_OPTIONS[value][0].join("|"));
  }

  const status = workspace?.status || {};
  const impact = workspace?.map?.operational_impact || {};

  return (
    <section className="dispatcher-workspace">
      <header className="dispatcher-workspace__header">
        <div>
          <p>CONTROLLED TRAINING ENVIRONMENT</p>
          <h1>Dispatcher Operations</h1>
          <span>
            Observe territory, request safe operational changes, and respond to
            cyber-affected command handling.
          </span>
        </div>
        <button type="button" onClick={load}>Refresh workspace</button>
      </header>

      {error && <div className="dispatch-error"><TriangleAlert size={16} />{error}</div>}

      <div className="dispatch-metrics">
        {[
          ["Availability", `${status.dispatch_availability_percent ?? 0}%`, CircleGauge],
          ["SCADA", status.scada_state || "Unknown", ShieldCheck],
          ["Queue", status.command_queue_depth ?? 0, Command],
          ["Avg delay", `${status.average_command_delay_seconds ?? 0}s`, ListRestart],
          ["Workload", status.dispatcher_workload_level || "Normal", TrainFront],
        ].map(([label, value, Icon]) => (
          <article key={label}><Icon size={18} /><span>{label}</span><strong>{value}</strong></article>
        ))}
      </div>

      <div className="dispatch-primary">
        <div className="dispatch-map"><RailroadMap /></div>
        <aside className="dispatch-side">
          <section className="dispatch-panel">
            <h2>Active trains</h2>
            <div className="dispatch-trains">
              {(workspace?.map?.trains || []).map((train) => (
                <button key={train.id} type="button" onClick={() => {
                  setTargetType("TRAIN");
                  setTargetId(String(train.id));
                  setCommandChoice("HOLD_TRAIN|Held");
                }}>
                  <TrainFront size={16} />
                  <strong>{train.symbol}</strong>
                  <span>MP {Number(train.milepost).toFixed(2)} · {train.speed} mph</span>
                  <small>{train.status} · {train.current_signal}</small>
                </button>
              ))}
            </div>
          </section>

          <section className="dispatch-panel">
            <h2>Command center</h2>
            <label>Target type
              <select value={targetType} onChange={(e) => changeTargetType(e.target.value)}>
                {Object.keys(COMMAND_OPTIONS).map((type) => <option key={type}>{type}</option>)}
              </select>
            </label>
            <label>Target
              <select value={targetId} onChange={(e) => setTargetId(e.target.value)}>
                <option value="">Select an asset</option>
                {collections[targetType].map((item) => (
                  <option key={item.id} value={item.id}>{item.name || item.symbol}</option>
                ))}
              </select>
            </label>
            <label>Validated command
              <select value={commandChoice} onChange={(e) => setCommandChoice(e.target.value)}>
                {options.map(([type, state]) => (
                  <option key={`${type}-${state}`} value={`${type}|${state}`}>
                    {type.replaceAll("_", " ")} → {state}
                  </option>
                ))}
              </select>
            </label>
            <p className="dispatch-preview">
              Backend safety validation runs before execution and again before
              queued commands execute. State is never applied optimistically.
            </p>
            <button disabled={busy || !targetId} onClick={() => {
              const [command_type, requested_state] = commandChoice.split("|");
              act(() => submitDispatchCommand({
                command_type, requested_state, target_type: targetType,
                target_id: Number(targetId), requested_by: "Dispatcher",
                priority: command_type === "HOLD_TRAIN" ? "Safety" : "Normal",
                payload: command_type === "APPLY_SPEED_RESTRICTION"
                  ? { speed_mph: Number(requested_state), reason: "Dispatcher restriction" }
                  : {},
              }));
            }}>Submit command</button>
          </section>

          <section className="dispatch-panel">
            <h2>Recovery</h2>
            <button disabled={busy || targetType !== "OT_DEVICE" || !targetId}
              onClick={() => act(() => submitRecoveryAction({
                action_type: "RESTORE_KNOWN_GOOD", target_id: Number(targetId),
                requested_by: "Dispatcher",
              }))}>
              Restore selected device to known-good
            </button>
          </section>
        </aside>
      </div>

      <div className="dispatch-secondary">
        <section className="dispatch-panel dispatch-table">
          <h2>Command queue</h2>
          <table><thead><tr><th>Command</th><th>Target</th><th>State</th><th>Status</th><th>Delay</th><th>Action</th></tr></thead>
            <tbody>{(workspace?.commands || []).slice(0, 15).map((item) => (
              <tr key={item.id} className={`is-${String(item.status).toLowerCase()}`}>
                <td>{item.command_type}</td><td>{item.target_type} {item.target_id}</td>
                <td>{item.requested_state}</td><td>{item.status}<small>{item.failure_reason}</small></td>
                <td>{item.delay_seconds || 0}s</td>
                <td>{["Pending", "Queued", "Blocked", "Failed"].includes(item.status) &&
                  <button onClick={() => act(() => cancelDispatchCommand(item.id))}>Cancel</button>}
                  {["Failed", "Blocked", "Cancelled"].includes(item.status) &&
                  <button onClick={() => act(() => retryDispatchCommand(item.id))}>Retry</button>}</td>
              </tr>
            ))}</tbody>
          </table>
        </section>

        <section className="dispatch-panel">
          <h2><Route size={17} /> Route request</h2>
          <select value={routeForm.train_id} onChange={(e) => setRouteForm({...routeForm, train_id:e.target.value})}>
            <option value="">Train</option>{collections.TRAIN.map((t)=><option key={t.id} value={t.id}>{t.symbol}</option>)}
          </select>
          {["start_block_id", "destination_block_id"].map((field) => (
            <select key={field} value={routeForm[field]} onChange={(e)=>setRouteForm({...routeForm,[field]:e.target.value})}>
              <option value="">{field === "start_block_id" ? "Start block" : "Destination block"}</option>
              {collections.TRACK_BLOCK.map((b)=><option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          ))}
          <button disabled={busy || Object.values(routeForm).some((v)=>!v)}
            onClick={()=>act(()=>submitDispatchRoute({
              ...routeForm, train_id:Number(routeForm.train_id),
              start_block_id:Number(routeForm.start_block_id),
              destination_block_id:Number(routeForm.destination_block_id),
              requested_by:"Dispatcher",
            }))}>Request route</button>
          <ul>{(workspace?.routes || []).slice(0,5).map((r)=><li key={r.id}><strong>{r.train}</strong> · {r.status}<span>{r.blocking_reason}</span></li>)}</ul>
        </section>

        <section className="dispatch-panel">
          <h2>Restrictions</h2>
          <input value={restrictionReason} onChange={(e)=>setRestrictionReason(e.target.value)} placeholder="Reason for selected target" />
          <button disabled={busy || !targetId || !restrictionReason}
            onClick={()=>act(()=>submitRestriction({
              restriction_type: targetType === "TRAIN" ? "HOLD_TRAIN" : "BLOCK_TRACK",
              target_type: targetType, target_id:Number(targetId),
              reason:restrictionReason, severity:"Medium", created_by:"Dispatcher",
            }))}>Apply restriction</button>
          <ul>{(workspace?.restrictions || []).map((r)=><li key={r.id}><strong>{r.restriction_type}</strong><span>{r.reason}</span><button onClick={()=>act(()=>clearRestriction(r.id))}>Clear</button></li>)}</ul>
        </section>

        <section className="dispatch-panel">
          <h2>Operations timeline</h2>
          <ul>{(workspace?.map?.timeline || []).slice(0,8).map((event)=><li key={event.id}><strong>{event.title}</strong><span>{event.message}</span></li>)}</ul>
          <p>{impact.summary}</p>
        </section>
      </div>
    </section>
  );
}
