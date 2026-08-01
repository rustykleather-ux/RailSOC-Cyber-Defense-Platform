import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BookOpenCheck,
  CircleGauge,
  Clock3,
  Copy,
  FileDown,
  GraduationCap,
  Lightbulb,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Square,
  Target,
  TimerReset,
  Trash2,
} from "lucide-react";
import {
  cloneExercise,
  clearExerciseRuns,
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
  finishExerciseRun,
  getExerciseWalkthrough,
  revealExerciseWalkthrough,
  validateExercise,
} from "../services/exerciseService";
import "./ExerciseCenter.css";
import "./ExerciseCenterExtras.css";

const blankExercise = {
  name: "", description: "", category: "Custom", difficulty: "Medium",
  estimated_duration: 20, recommended_players: 1, enabled: true,
  known_intelligence: "", success_criteria: "", failure_conditions: "",
  objectives: [], script_events: [], hints: [], metadata: {},
  walkthrough: {
    overview: "", prerequisites: [], troubleshooting: [],
    expected_end_state: [], instructor_notes: "", steps: [],
  },
};

function clock(seconds = 0) {
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function WalkthroughPanel({ walkthrough, instructorMode, onReveal }) {
  if (!walkthrough?.steps) {
    return <section className="exercise-panel walkthrough-spoiler">
      <GraduationCap size={24}/><h3>Answer Sheet / Walkthrough</h3>
      <p>{walkthrough?.available===false?"No walkthrough provided.":"This instructor answer sheet contains mission spoilers."}</p>
      {walkthrough?.available!==false&&<button onClick={onReveal}>Reveal answer sheet</button>}
    </section>;
  }
  return <section className="exercise-panel walkthrough-panel">
    <div className="walkthrough-heading"><div><p>INSTRUCTOR-GUIDED ANSWER SHEET</p><h3>Walkthrough</h3></div><span>{walkthrough.steps.filter((step)=>step.verification_status==="Completed").length}/{walkthrough.steps.length} verified</span></div>
    <p>{walkthrough.overview}</p>
    {walkthrough.steps.map((step)=><details key={step.id||step.step_number} open={step.verification_status==="Blocked"}>
      <summary><b>{step.step_number}. {step.title}</b><span className={`walkthrough-state is-${step.verification_status.toLowerCase().replace(" ","-")}`}>{step.verification_status}</span></summary>
      <p><strong>Purpose:</strong> {step.purpose}</p>
      <p><strong>Required action:</strong> {step.player_action}</p>
      <p><strong>Expected result:</strong> {step.expected_result}</p>
      <code>{step.verification_condition}</code>
      {step.blocking_reasons?.length>0&&<div className="walkthrough-blockers"><strong>Current blocker</strong>{step.blocking_reasons.map((reason)=><p key={`${reason.type}-${reason.id||reason.label}`}>{reason.label} · {reason.status}</p>)}</div>}
      {step.common_mistakes?.length>0&&<p><strong>Common mistakes:</strong> {step.common_mistakes.join("; ")}</p>}
      {step.recovery_path&&<p><strong>Recovery path:</strong> {step.recovery_path}</p>}
      {step.hint&&<p><strong>Hint:</strong> {step.hint}</p>}
      {instructorMode&&step.instructor_notes&&<p className="instructor-note"><strong>Instructor:</strong> {step.instructor_notes}</p>}
      {step.navigation_location&&<a href={step.navigation_location}>Open relevant panel</a>}
    </details>)}
  </section>;
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
  const [instructorMode, setInstructorMode] = useState(false);
  const [activeTab, setActiveTab] = useState("live");
  const [walkthrough, setWalkthrough] = useState(null);
  const [validation, setValidation] = useState(null);

  const loadLibrary = useCallback(async () => {
    try {
      const [items, history] = await Promise.all([
        getExercises({ ...filters, instructor: instructorMode }), getExerciseRuns(),
      ]);
      setExercises(items);
      setRuns(history);
      setSelected((current) =>
        current ? items.find((item) => item.id === current.id) || items[0] : items[0],
      );
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  }, [filters, instructorMode]);

  const loadRun = useCallback(async () => {
    if (!run?.id) return;
    try {
      const next = await getExerciseRun(run.id, instructorMode);
      setRun(next);
      if (instructorMode || next.walkthrough_revealed) {
        setWalkthrough(await getExerciseWalkthrough(
          next.exercise_id, next.id, instructorMode,
        ));
      }
      if (["Completed", "Failed", "Cancelled"].includes(next.status)) {
        setReport(await getAfterActionReport(next.id));
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  }, [run?.id, instructorMode]);

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

  async function clearHistory() {
    const confirmed = window.confirm(
      "Clear all exercise run history, checkpoints, scores, and run timelines? Exercise definitions will be preserved.",
    );
    if (!confirmed) return;
    const result = await act(() => clearExerciseRuns());
    if (result) {
      setRun(null);
      setReport(null);
      setRuns([]);
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
  function addWalkthroughStep() {
    setDraft((item) => ({
      ...item,
      walkthrough: {
        ...(item.walkthrough || blankExercise.walkthrough),
        steps: [...(item.walkthrough?.steps || []), {
          title: "New walkthrough step",
          player_action: "",
          navigation_location: "/exercises",
          expected_result: "",
          verification_condition: "",
          action_id: "VIEW_OBJECTIVES",
          objective_index: 0,
          common_mistakes: [],
          player_visible: true,
        }],
      },
    }));
  }

  async function finishCurrentRun() {
    try {
      const finished = await finishExerciseRun(run.id, false);
      setRun(finished);
    } catch (err) {
      if (err.response?.status === 409 && window.confirm(
        `${err.response.data.detail}\n\nCancel this incomplete exercise?`,
      )) {
        setRun(await finishExerciseRun(run.id, true));
      } else if (err.response?.status !== 409) {
        setError(err.response?.data?.detail || err.message);
      }
    }
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
        <label className="instructor-mode-toggle">
          <input
            type="checkbox"
            checked={instructorMode}
            onChange={(event) => setInstructorMode(event.target.checked)}
          />
          <GraduationCap size={15} /> Instructor Mode
        </label>
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
              }}>{["device_status","communications_restored","track_availability_min","train_delay_max","dispatch_availability_min","no_unsafe_routing","incidents_resolved","command_queue_max","elapsed_max","action_count","event_sequence","sustained_metric"].map((x)=><option key={x}>{x}</option>)}</select>
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
          <section className="walkthrough-builder">
            <h3>Answer Sheet / Walkthrough</h3>
            <label>Overview<textarea
              value={draft.walkthrough?.overview || ""}
              onChange={(e)=>setDraft({...draft,walkthrough:{...(draft.walkthrough||{}),overview:e.target.value}})}
            /></label>
            {(draft.walkthrough?.steps || []).map((step,index)=><article key={index}>
              <input value={step.title} placeholder="Step title" onChange={(e)=>{
                const steps=[...draft.walkthrough.steps];steps[index]={...step,title:e.target.value};setDraft({...draft,walkthrough:{...draft.walkthrough,steps}});
              }}/>
              <input value={step.player_action} placeholder="Required player action" onChange={(e)=>{
                const steps=[...draft.walkthrough.steps];steps[index]={...step,player_action:e.target.value};setDraft({...draft,walkthrough:{...draft.walkthrough,steps}});
              }}/>
              <select value={step.navigation_location} onChange={(e)=>{
                const steps=[...draft.walkthrough.steps];steps[index]={...step,navigation_location:e.target.value};setDraft({...draft,walkthrough:{...draft.walkthrough,steps}});
              }}>{["/exercises","/incidents","/assets","/dispatcher","/topology","/network"].map((x)=><option key={x}>{x}</option>)}</select>
              <select value={step.action_id} onChange={(e)=>{
                const steps=[...draft.walkthrough.steps];steps[index]={...step,action_id:e.target.value};setDraft({...draft,walkthrough:{...draft.walkthrough,steps}});
              }}>{["VIEW_ASSET","ACKNOWLEDGE_INCIDENT","ASSIGN_INCIDENT","ADD_INVESTIGATION_NOTES","ISOLATE_DEVICE","RESTORE_KNOWN_GOOD","RESTORE_COMMUNICATIONS","CLOSE_INCIDENT","VIEW_OPERATIONAL_IMPACT","VIEW_OBJECTIVES","FINISH_EXERCISE"].map((x)=><option key={x}>{x}</option>)}</select>
              <select value={step.objective_index ?? ""} onChange={(e)=>{
                const steps=[...draft.walkthrough.steps];steps[index]={...step,objective_index:e.target.value===""?null:Number(e.target.value)};setDraft({...draft,walkthrough:{...draft.walkthrough,steps}});
              }}><option value="">No linked objective</option>{draft.objectives.map((objective,objectiveIndex)=><option value={objectiveIndex} key={objectiveIndex}>{objective.description}</option>)}</select>
              <input value={step.expected_result} placeholder="Expected result" onChange={(e)=>{
                const steps=[...draft.walkthrough.steps];steps[index]={...step,expected_result:e.target.value};setDraft({...draft,walkthrough:{...draft.walkthrough,steps}});
              }}/>
              <input value={step.verification_condition} placeholder="Verification condition" onChange={(e)=>{
                const steps=[...draft.walkthrough.steps];steps[index]={...step,verification_condition:e.target.value};setDraft({...draft,walkthrough:{...draft.walkthrough,steps}});
              }}/>
            </article>)}
            <button type="button" onClick={addWalkthroughStep}><Plus size={14}/>Walkthrough step</button>
          </section>
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
              if(created){setRun(created);setActiveTab("live");setWalkthrough(null);}
            }}><Play size={15}/>Create run</button>
            <button onClick={()=>act(()=>cloneExercise(selected.id,`${selected.name} Custom`).then((r)=>r.data))}><Copy size={15}/>Clone</button></div>
            <div className="exercise-actions">
              <button onClick={()=>{setDraft(selected);setBuilderOpen(true);}}>Edit</button>
              <button onClick={async()=>{
                const removed=await act(()=>deleteExercise(selected.id));
                if(removed)setSelected(null);
              }}>Delete</button>
              <a href={exerciseExportUrl(selected.id, instructorMode)}>
                <FileDown size={14}/>Export JSON
              </a>
              {instructorMode && <button onClick={async()=>{
                const result=await act(()=>validateExercise(selected.id));
                if(result)setValidation(result);
              }}><BookOpenCheck size={14}/>Validate Exercise</button>}
            </div>
            {validation?.exercise_id===selected.id&&<section className={`exercise-validation ${validation.completion_readiness?"is-ready":"has-errors"}`}>
              <strong>{validation.completion_readiness?"Completion ready":"Configuration needs attention"}</strong>
              <span>{validation.objective_coverage.covered}/{validation.objective_coverage.required} required objectives covered</span>
              {validation.errors.map((item)=><p key={item}>{item}</p>)}
              {validation.warnings.map((item)=><p key={item}>Warning: {item}</p>)}
            </section>}
          </section>}

          {run && <div className="running-exercise">
            <section className="run-banner"><div><p>{run.current_phase}</p><h2>{run.exercise_name}</h2><span className={`run-status is-${run.status.toLowerCase()}`}>{run.status}</span></div>
              <strong>{clock(run.elapsed_seconds)}</strong>
              <div>{run.status==="Ready"&&<button onClick={()=>act(()=>exerciseRunAction(run.id,"start"))}><Play size={14}/>Start</button>}
                {run.status==="Running"&&<button onClick={()=>act(()=>exerciseRunAction(run.id,"pause"))}><Pause size={14}/>Pause</button>}
                {run.status==="Paused"&&<button onClick={()=>act(()=>exerciseRunAction(run.id,"resume"))}><Play size={14}/>Resume</button>}
                {!["Completed","Failed","Cancelled"].includes(run.status)&&<button onClick={finishCurrentRun}><BookOpenCheck size={14}/>Finish</button>}
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
            <nav className="exercise-run-tabs">
              {["live","objectives","timeline","score","walkthrough","after-action"].map((tab)=><button
                key={tab}
                className={activeTab===tab?"is-active":""}
                onClick={async()=>{
                  setActiveTab(tab);
                  if(tab==="walkthrough"&&(instructorMode||run.walkthrough_revealed)){
                    setWalkthrough(await getExerciseWalkthrough(run.exercise_id,run.id,instructorMode));
                  }
                }}
              >{tab==="walkthrough"?"Answer Sheet":tab.replace("-"," ")}</button>)}
            </nav>
            <div className="run-grid">
              {activeTab==="objectives"&&<section className="exercise-panel exercise-objective-diagnostics"><h3>Objectives</h3>{visibleObjectives.map((item)=><article className="objective" key={item.run_objective_id}><div><strong>{item.description}</strong><span>{item.status}</span></div><progress max="100" value={item.progress}/><small>{item.progress}% complete · {item.mode}</small>{instructorMode&&<div className="objective-debug"><code>{item.expected_condition}</code>{item.blocking_reasons?.map((reason)=><p key={`${reason.type}-${reason.id||reason.label}`}>{reason.label} · {reason.status}</p>)}</div>}</article>)}</section>}
              {activeTab==="live"&&<><section className="exercise-panel"><h3>Hints</h3><button disabled={busy} onClick={()=>act(()=>requestExerciseHint(run.id))}><Lightbulb size={14}/>Request hint</button>{run.timeline.filter((x)=>x.event_type==="exercise_hint"||x.event_type==="exercise_display_hint").map((x)=><article key={x.id}><strong>{x.title}</strong><span>{x.message}</span></article>)}</section><section className="exercise-panel"><h3>Checkpoints</h3><button onClick={()=>act(()=>createCheckpoint(run.id,`Checkpoint ${run.checkpoints.length+1}`))}><TimerReset size={14}/>Save checkpoint</button>{run.checkpoints.map((item)=><article key={item.id}><strong>{item.name}</strong><span>{clock(item.elapsed_seconds)}</span><button onClick={()=>act(()=>restoreCheckpoint(run.id,item.id))}>Restore</button></article>)}</section></>}
              {activeTab==="timeline"&&<section className="exercise-panel exercise-timeline"><h3>Exercise Timeline</h3>{run.timeline.map((item)=><article key={item.id}><time>{new Date(item.timestamp).toLocaleTimeString()}</time><strong>{item.title}</strong><span>{item.message}</span></article>)}</section>}
              {activeTab==="score"&&<section className="exercise-panel"><h3>Scoring</h3>{scoreboard.map(([label,value])=><article key={label}><strong>{label}</strong><span>{Number(value||0).toFixed(1)}</span></article>)}{run.terminal_reason&&<p><strong>Final reason:</strong> {run.terminal_reason}</p>}</section>}
              {activeTab==="walkthrough"&&<WalkthroughPanel walkthrough={walkthrough||run.walkthrough||{available:run.walkthrough_available}} instructorMode={instructorMode} onReveal={async()=>{
                if(window.confirm("Reveal the answer sheet? This contains spoilers and may apply a score penalty.")){
                  const revealed=await act(()=>revealExerciseWalkthrough(run.id));
                  if(revealed)setWalkthrough(revealed);
                }
              }}/>}
            </div>
            {activeTab==="after-action"&&report&&<section className="after-action"><h2>After-Action Report</h2><p>{report.mission_summary}</p><p><strong>Final reason:</strong> {report.completion_reason||report.failure_reason||report.cancellation_reason}</p><div><a href={reportDownloadUrl(run.id,"markdown")}><FileDown size={14}/>Markdown</a><a href={reportDownloadUrl(run.id,"pdf")}><FileDown size={14}/>PDF</a><a href={reportDownloadUrl(run.id,"json")}><FileDown size={14}/>JSON</a></div><pre>{report.markdown}</pre></section>}
            <button className="return-library" onClick={()=>{setRun(null);setReport(null);}}>Return to library</button>
          </div>}
        </main>
      </div>
      <section className="exercise-history">
        <div className="exercise-history__header">
          <div>
            <h2>Exercise History</h2>
            <span>Saved runs, scores, checkpoints, and after-action records.</span>
          </div>
          <button
            className="exercise-history__clear"
            disabled={busy || runs.some((item) =>
              ["Running", "Paused"].includes(item.status)
            )}
            onClick={clearHistory}
            title="Active exercises must be cancelled or completed first."
          >
            <Trash2 size={14} />
            Clear history
          </button>
        </div>
        {runs.length === 0 && (
          <p className="exercise-history__empty">No exercise history recorded.</p>
        )}
        {runs.slice(0,8).map((item)=><button key={item.id} onClick={async()=>setRun(await getExerciseRun(item.id,instructorMode))}><strong>{item.exercise_name}</strong><span>{item.status} · Score {item.score} · {clock(item.elapsed_seconds)}</span></button>)}
      </section>
    </section>
  );
}
