import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BookOpenCheck,
  CircleGauge,
  Clock3,
  Copy,
  FileDown,
  Lightbulb,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Square,
  Target,
  TimerReset,
} from "lucide-react";
import {
  cloneExercise,
  createCheckpoint,
  createExercise,
  createExerciseRun,
  deleteExercise,
  exerciseExportUrl,
  exerciseRunAction,
  getAfterActionReport,
  getExerciseRun,
  getExerciseRuns,
  getExercises,
  reportDownloadUrl,
  requestExerciseHint,
  restoreCheckpoint,
  updateExercise,
} from "../services/exerciseService";
import "./ExerciseCenter.css";
import "./ExerciseCenterExtras.css";

const blankExercise = {
  name: "", description: "", category: "Custom", difficulty: "Medium",
  estimated_duration: 20, recommended_players: 1, enabled: true,
  known_intelligence: "", success_criteria: "", failure_conditions: "",
  objectives: [], script_events: [], hints: [], metadata: {},
};

function clock(seconds = 0) {
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

export default function ExerciseCenter() {
  const [exercises, setExercises] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selected, setSelected] = useState(null);
  const [run, setRun] = useState(null);
  const [report, setReport] = useState(null);
  const [filters, setFilters] = useState({ category: "", difficulty: "" });
  const [builderOpen, setBuilderOpen] = useState(false);
  const [draft, setDraft] = useState(blankExercise);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadLibrary = useCallback(async () => {
    try {
      const [items, history] = await Promise.all([
        getExercises(filters), getExerciseRuns(),
      ]);
      setExercises(items);
      setRuns(history);
      setSelected((current) =>
        current ? items.find((item) => item.id === current.id) || items[0] : items[0],
      );
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  }, [filters]);

  const loadRun = useCallback(async () => {
    if (!run?.id) return;
    try {
      const next = await getExerciseRun(run.id);
      setRun(next);
      if (["Completed", "Failed", "Cancelled"].includes(next.status)) {
        setReport(await getAfterActionReport(next.id));
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  }, [run?.id]);

  useEffect(() => { loadLibrary(); }, [loadLibrary]);
  useEffect(() => {
    if (!run?.id) return undefined;
    const timer = window.setInterval(loadRun, 3000);
    return () => window.clearInterval(timer);
  }, [run?.id, loadRun]);

  async function act(callback) {
    setBusy(true);
    try {
      const result = await callback();
      if (result?.id && result?.exercise_id) setRun(result);
      await loadLibrary();
      setError("");
      return result;
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      return null;
    } finally {
      setBusy(false);
    }
  }

  const completedObjectives = run?.objectives?.filter(
    (item) => item.status === "Completed",
  ).length || 0;
  const visibleObjectives = run?.objectives?.filter(
    (item) => item.status !== "Hidden",
  ) || [];
  const activeIncidents =
    run?.briefing?.current_railroad_status?.open_incidents ??
    run?.timeline?.filter((item) => item.event_type.includes("incident")).length ??
    0;
  const scoreboard = useMemo(() => run ? [
    ["Overall", run.score, CircleGauge],
    ["Cyber", run.cyber_score, BookOpenCheck],
    ["Operations", run.operations_score, Target],
    ["Safety", run.safety_score, Target],
    ["Availability", run.availability_score, CircleGauge],
    ["Response", run.response_score, Clock3],
  ] : [], [run]);

  function addObjective() {
    setDraft((item) => ({
      ...item,
      objectives: [...item.objectives, {
        description: "Maintain track availability above 90%.",
        objective_type: "track_availability_min",
        target_value: 90, comparison: "gte",
      }],
    }));
  }
  function addEvent() {
    setDraft((item) => ({
      ...item,
      script_events: [...item.script_events, {
        event_type: "display_message", offset_seconds: 0,
        payload: { title: "Instructor inject", message: "New exercise event." },
      }],
    }));
  }
  function addHint() {
    setDraft((item) => ({
      ...item,
      hints: [...item.hints, {
        message: "Review the current incident and operational-impact state.",
        available_after_seconds: 120, automatic: false,
      }],
    }));
  }

  return (
    <section className="exercise-center">
      <header className="exercise-center__header">
        <div><p>TRACKSENTINEL TRAINING ORCHESTRATION</p><h1>Exercise Center</h1>
          <span>Instructor-led railroad OT cyber missions, live scoring, and after-action review.</span>
        </div>
        <button onClick={() => setBuilderOpen((value) => !value)}>
          <Plus size={16} /> Visual Exercise Builder
        </button>
        <label className="exercise-import">
          Import JSON
          <input type="file" accept="application/json" onChange={async(e)=>{
            const file=e.target.files?.[0]; if(!file)return;
            const imported=JSON.parse(await file.text());
            await act(()=>createExercise({
              ...imported,
              name:`${imported.name} Imported`,
            }).then((response)=>response.data));
            e.target.value="";
          }}/>
        </label>
      </header>
      {error && <div className="exercise-error">{error}</div>}

      {builderOpen && (
        <section className="exercise-builder">
          <h2>Visual Exercise Builder</h2>
          <div className="exercise-builder__grid">
            <label>Name<input value={draft.name} onChange={(e)=>setDraft({...draft,name:e.target.value})}/></label>
            <label>Category<select value={draft.category} onChange={(e)=>setDraft({...draft,category:e.target.value})}>
              {["Incident Response","Signals","PTC","Communications","SCADA","Dispatcher","Operations","Power","Custom"].map((x)=><option key={x}>{x}</option>)}
            </select></label>
            <label>Difficulty<select value={draft.difficulty} onChange={(e)=>setDraft({...draft,difficulty:e.target.value})}>
              {["Easy","Medium","Hard","Expert"].map((x)=><option key={x}>{x}</option>)}
            </select></label>
            <label>Duration (minutes)<input type="number" min="1" value={draft.estimated_duration} onChange={(e)=>setDraft({...draft,estimated_duration:Number(e.target.value)})}/></label>
          </div>
          <label>Description<textarea value={draft.description} onChange={(e)=>setDraft({...draft,description:e.target.value})}/></label>
          <div className="exercise-builder__columns">
            <div><h3>Objectives</h3>{draft.objectives.map((item,index)=><article key={index}>
              <select value={item.objective_type} onChange={(e)=>{
                const next=[...draft.objectives]; next[index]={...item,objective_type:e.target.value}; setDraft({...draft,objectives:next});
              }}>{["device_status","communications_restored","track_availability_min","train_delay_max","dispatch_availability_min","no_unsafe_routing","incidents_resolved","command_queue_max","elapsed_max"].map((x)=><option key={x}>{x}</option>)}</select>
              <input value={item.description} onChange={(e)=>{const next=[...draft.objectives];next[index]={...item,description:e.target.value};setDraft({...draft,objectives:next});}}/>
              <input type="number" placeholder="Target value" value={item.target_value ?? ""} onChange={(e)=>{const next=[...draft.objectives];next[index]={...item,target_value:Number(e.target.value)};setDraft({...draft,objectives:next});}}/>
              {["device_status","communications_restored"].includes(item.objective_type)&&
                <input type="number" placeholder="Target device ID" value={item.target_id ?? ""} onChange={(e)=>{const next=[...draft.objectives];next[index]={...item,target_type:"OT_DEVICE",target_id:Number(e.target.value),metadata:{status:"Online"}};setDraft({...draft,objectives:next});}}/>}
            </article>)}<button onClick={addObjective}><Plus size={14}/>Objective</button></div>
            <div><h3>Timeline events</h3>{draft.script_events.map((item,index)=><article key={index}>
              <select value={item.event_type} onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,event_type:e.target.value};setDraft({...draft,script_events:next});}}>
                {["wait","display_message","launch_attack","spawn_incident","restore_asset","dispatch_train","spawn_train","inject_alert","display_hint","change_weather","pause","resume","end_exercise"].map((x)=><option key={x}>{x}</option>)}
              </select>
              <input type="number" min="0" value={item.offset_seconds} onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,offset_seconds:Number(e.target.value)};setDraft({...draft,script_events:next});}}/>
              <input value={item.payload?.message || ""} placeholder="Message" onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,payload:{...item.payload,message:e.target.value}};setDraft({...draft,script_events:next});}}/>
              {item.event_type==="launch_attack"&&<>
                <select value={item.payload?.attack_id || "logic_modification"} onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,payload:{...item.payload,attack_id:e.target.value}};setDraft({...draft,script_events:next});}}>
                  {["logic_modification","credential_abuse","network_recon","firmware_tampering","denial_of_service","communication_failure","malware_injection","ransomware_attack","sensor_tampering","power_fluctuation"].map((x)=><option key={x}>{x}</option>)}
                </select>
                <input type="number" placeholder="Target device ID" value={item.payload?.target_ids?.[0] || ""} onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,payload:{...item.payload,target_ids:e.target.value?[Number(e.target.value)]:[]}};setDraft({...draft,script_events:next});}}/>
              </>}
              {item.event_type==="restore_asset"&&<>
                <select value={item.payload?.action_type || "RESTORE_KNOWN_GOOD"} onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,payload:{...item.payload,action_type:e.target.value}};setDraft({...draft,script_events:next});}}>
                  {["RESTORE_KNOWN_GOOD","RESTORE_COMMUNICATIONS","ISOLATE_DEVICE","TRANSFER_TO_BACKUP","PLACE_IN_SAFE_MODE","REVOKE_REMOTE_ACCESS","CLEAR_ATTACK_EFFECT"].map((x)=><option key={x}>{x}</option>)}
                </select>
                <input type="number" placeholder="Target device ID" value={item.payload?.target_id || ""} onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,payload:{...item.payload,target_id:Number(e.target.value)}};setDraft({...draft,script_events:next});}}/>
              </>}
              {item.event_type==="spawn_train"&&<>
                <input placeholder="Train symbol" value={item.payload?.symbol || ""} onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,payload:{...item.payload,symbol:e.target.value}};setDraft({...draft,script_events:next});}}/>
                <input type="number" placeholder="Milepost" value={item.payload?.milepost || 80} onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,payload:{...item.payload,milepost:Number(e.target.value)}};setDraft({...draft,script_events:next});}}/>
              </>}
              {item.event_type==="dispatch_train"&&<>
                <select value={item.payload?.command_type || "HOLD_TRAIN"} onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,payload:{...item.payload,command_type:e.target.value,target_type:"TRAIN",requested_state:e.target.value==="HOLD_TRAIN"?"Held":"Released"}};setDraft({...draft,script_events:next});}}>
                  <option>HOLD_TRAIN</option><option>RELEASE_TRAIN</option>
                </select>
                <input type="number" placeholder="Train ID" value={item.payload?.target_id || ""} onChange={(e)=>{const next=[...draft.script_events];next[index]={...item,payload:{...item.payload,target_type:"TRAIN",target_id:Number(e.target.value),requested_by:"Exercise Engine",priority:"Safety"}};setDraft({...draft,script_events:next});}}/>
              </>}
            </article>)}<button onClick={addEvent}><Plus size={14}/>Event</button></div>
            <div><h3>Hints</h3>{draft.hints.map((item,index)=><article key={index}>
              <input value={item.message} onChange={(e)=>{const next=[...draft.hints];next[index]={...item,message:e.target.value};setDraft({...draft,hints:next});}}/>
              <input type="number" min="0" value={item.available_after_seconds} onChange={(e)=>{const next=[...draft.hints];next[index]={...item,available_after_seconds:Number(e.target.value)};setDraft({...draft,hints:next});}}/>
            </article>)}<button onClick={addHint}><Plus size={14}/>Hint</button></div>
          </div>
          <button disabled={busy || !draft.name} onClick={async()=>{
            const created=await act(()=>(draft.id
              ? updateExercise(draft.id,draft)
              : createExercise(draft)).then((r)=>r.data));
            if(created){setDraft(blankExercise);setBuilderOpen(false);}
          }}>{draft.id?"Update exercise":"Save exercise"}</button>
        </section>
      )}

      <div className="exercise-layout">
        <aside className="exercise-library">
          <div className="exercise-filters">
            <select value={filters.category} onChange={(e)=>setFilters({...filters,category:e.target.value})}><option value="">All categories</option>{["Incident Response","Signals","PTC","Communications","SCADA","Dispatcher","Operations","Power","Custom"].map((x)=><option key={x}>{x}</option>)}</select>
            <select value={filters.difficulty} onChange={(e)=>setFilters({...filters,difficulty:e.target.value})}><option value="">All difficulty</option>{["Easy","Medium","Hard","Expert"].map((x)=><option key={x}>{x}</option>)}</select>
          </div>
          <h2>Exercise Library</h2>
          {exercises.map((item)=><button className={selected?.id===item.id?"is-selected":""} key={item.id} onClick={()=>setSelected(item)}>
            <strong>{item.name}</strong><span>{item.category} · {item.difficulty}</span><small>{item.estimated_duration} min · {item.recommended_players} player(s)</small>
          </button>)}
        </aside>

        <main className="exercise-main">
          {selected && !run && <section className="mission-briefing">
            <p>MISSION BRIEFING</p><h2>{selected.name}</h2><span>{selected.description}</span>
            <dl><div><dt>Difficulty</dt><dd>{selected.difficulty}</dd></div><div><dt>Duration</dt><dd>{selected.estimated_duration} minutes</dd></div><div><dt>Players</dt><dd>{selected.recommended_players}</dd></div></dl>
            <h3>Known intelligence</h3><p>{selected.known_intelligence}</p>
            <h3>Objectives</h3><ul>{selected.objectives.filter((x)=>!x.hidden).map((x)=><li key={x.id}>{x.description}{x.optional&&" (Optional)"}</li>)}</ul>
            <h3>Success criteria</h3><p>{selected.success_criteria}</p><h3>Failure conditions</h3><p>{selected.failure_conditions}</p>
            <div className="exercise-actions"><button disabled={busy} onClick={async()=>{
              const created=await act(()=>createExerciseRun(selected.id));
              if(created) setRun(created);
            }}><Play size={15}/>Create run</button>
            <button onClick={()=>act(()=>cloneExercise(selected.id,`${selected.name} Custom`).then((r)=>r.data))}><Copy size={15}/>Clone</button></div>
            <div className="exercise-actions">
              <button onClick={()=>{setDraft(selected);setBuilderOpen(true);}}>Edit</button>
              <button onClick={async()=>{
                const removed=await act(()=>deleteExercise(selected.id));
                if(removed)setSelected(null);
              }}>Delete</button>
              <a href={exerciseExportUrl(selected.id)}>
                <FileDown size={14}/>Export JSON
              </a>
            </div>
          </section>}

          {run && <div className="running-exercise">
            <section className="run-banner"><div><p>{run.current_phase}</p><h2>{run.exercise_name}</h2><span className={`run-status is-${run.status.toLowerCase()}`}>{run.status}</span></div>
              <strong>{clock(run.elapsed_seconds)}</strong>
              <div>{run.status==="Ready"&&<button onClick={()=>act(()=>exerciseRunAction(run.id,"start"))}><Play size={14}/>Start</button>}
                {run.status==="Running"&&<button onClick={()=>act(()=>exerciseRunAction(run.id,"pause"))}><Pause size={14}/>Pause</button>}
                {run.status==="Paused"&&<button onClick={()=>act(()=>exerciseRunAction(run.id,"resume"))}><Play size={14}/>Resume</button>}
                {!["Completed","Failed","Cancelled"].includes(run.status)&&<button onClick={()=>act(()=>exerciseRunAction(run.id,"cancel"))}><Square size={14}/>Cancel</button>}
                <button onClick={()=>act(()=>exerciseRunAction(run.id,"restart"))}><RotateCcw size={14}/>Restart</button>
              </div>
            </section>
            {run.status==="Ready"&&<section className="mission-briefing run-briefing">
              <p>PRE-START MISSION BRIEFING</p>
              <h3>{run.briefing.description}</h3>
              <p><strong>Railroad status:</strong> {run.briefing.current_railroad_status.summary}</p>
              <p><strong>Known intelligence:</strong> {run.briefing.known_intelligence}</p>
              <p><strong>Success:</strong> {run.briefing.success_criteria}</p>
              <p><strong>Failure:</strong> {run.briefing.failure_conditions}</p>
            </section>}
            <section className="exercise-scoreboard">{scoreboard.map(([label,value,Icon])=><article key={label}><Icon size={17}/><span>{label}</span><strong>{Number(value||0).toFixed(0)}</strong></article>)}
              <article><Clock3 size={17}/><span>Objectives</span><strong>{completedObjectives}/{run.objectives.length}</strong></article>
              <article><Target size={17}/><span>Active incidents</span><strong>{activeIncidents}</strong></article>
            </section>
            <div className="run-grid">
              <section className="exercise-panel"><h3>Objectives</h3>{visibleObjectives.map((item)=><article className="objective" key={item.run_objective_id}><div><strong>{item.description}</strong><span>{item.status}</span></div><progress max="100" value={item.progress}/><small>{item.progress}% complete</small></article>)}</section>
              <section className="exercise-panel"><h3>Hints</h3><button disabled={busy} onClick={()=>act(()=>requestExerciseHint(run.id))}><Lightbulb size={14}/>Request hint</button>{run.timeline.filter((x)=>x.event_type==="exercise_hint"||x.event_type==="exercise_display_hint").map((x)=><article key={x.id}><strong>{x.title}</strong><span>{x.message}</span></article>)}</section>
              <section className="exercise-panel"><h3>Checkpoints</h3><button onClick={()=>act(()=>createCheckpoint(run.id,`Checkpoint ${run.checkpoints.length+1}`))}><TimerReset size={14}/>Save checkpoint</button>{run.checkpoints.map((item)=><article key={item.id}><strong>{item.name}</strong><span>{clock(item.elapsed_seconds)}</span><button onClick={()=>act(()=>restoreCheckpoint(run.id,item.id))}>Restore</button></article>)}</section>
              <section className="exercise-panel exercise-timeline"><h3>Exercise Timeline</h3>{run.timeline.map((item)=><article key={item.id}><time>{new Date(item.timestamp).toLocaleTimeString()}</time><strong>{item.title}</strong><span>{item.message}</span></article>)}</section>
            </div>
            {report && <section className="after-action"><h2>After-Action Report</h2><p>{report.mission_summary}</p><div><a href={reportDownloadUrl(run.id,"markdown")}><FileDown size={14}/>Markdown</a><a href={reportDownloadUrl(run.id,"pdf")}><FileDown size={14}/>PDF</a><a href={reportDownloadUrl(run.id,"json")}><FileDown size={14}/>JSON</a></div><pre>{report.markdown}</pre></section>}
            <button className="return-library" onClick={()=>{setRun(null);setReport(null);}}>Return to library</button>
          </div>}
        </main>
      </div>
      <section className="exercise-history"><h2>Exercise History</h2>{runs.slice(0,8).map((item)=><button key={item.id} onClick={async()=>setRun(await getExerciseRun(item.id))}><strong>{item.exercise_name}</strong><span>{item.status} · Score {item.score} · {clock(item.elapsed_seconds)}</span></button>)}</section>
    </section>
  );
}
