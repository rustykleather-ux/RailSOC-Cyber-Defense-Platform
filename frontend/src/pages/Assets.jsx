import { useEffect, useMemo, useState } from "react";
import DeviceInventory from "../components/DeviceInventory";
import {
  addRelationship,
  createDevice,
  createDeviceType,
  getCapabilities,
  getDevices,
  getDeviceTypes,
  getRelationshipTargets,
} from "../services/deviceService";

const emptyDevice = {
  name: "",
  device_type_id: "",
  vendor: "",
  model: "",
  firmware: "",
  location: "",
  subdivision: "",
  track: "Main",
  latitude: "",
  longitude: "",
  criticality: "Medium",
  description: "",
};

const emptyType = {
  name: "",
  description: "",
  category: "Custom",
  icon: "cpu",
  color: "#38bdf8",
  vendor: "",
  model: "",
  firmware_supported: "",
  default_capabilities: [],
  default_effects: [],
  default_metadata: {},
};

const relationshipDefaults = {
  TRACK_BLOCK: "CONTROLS_TRACK_BLOCK",
  TRACK_SWITCH: "CONTROLS_SWITCH",
  GRADE_CROSSING: "CONTROLS_CROSSING",
  OT_DEVICE: "CONNECTED_TO",
};

function Assets() {
  const [devices, setDevices] = useState([]);
  const [deviceTypes, setDeviceTypes] = useState([]);
  const [capabilities, setCapabilities] = useState([]);
  const [targets, setTargets] = useState({});
  const [deviceForm, setDeviceForm] = useState(emptyDevice);
  const [typeForm, setTypeForm] = useState(emptyType);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [targetType, setTargetType] = useState("TRACK_BLOCK");
  const [targetId, setTargetId] = useState("");
  const [panel, setPanel] = useState("inventory");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadData() {
    try {
      const [deviceResponse, typeResponse, capabilityResponse, targetResponse] =
        await Promise.all([
          getDevices(),
          getDeviceTypes(),
          getCapabilities(),
          getRelationshipTargets(),
        ]);
      setDevices(deviceResponse.data ?? []);
      setDeviceTypes(typeResponse.data ?? []);
      setCapabilities(capabilityResponse.data ?? []);
      setTargets(targetResponse.data ?? {});
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to load railroad assets.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const selectedType = useMemo(
    () =>
      deviceTypes.find(
        (item) => String(item.id) === String(deviceForm.device_type_id),
      ),
    [deviceTypes, deviceForm.device_type_id],
  );

  function changeDevice(event) {
    const { name, value } = event.target;
    setDeviceForm((current) => ({ ...current, [name]: value }));
  }

  async function submitDevice(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {
        ...deviceForm,
        device_type_id: Number(deviceForm.device_type_id),
        latitude: deviceForm.latitude === "" ? null : Number(deviceForm.latitude),
        longitude:
          deviceForm.longitude === "" ? null : Number(deviceForm.longitude),
      };
      const response = await createDevice(payload);
      setNotice(`${response.data.name} created.`);
      setDeviceForm(emptyDevice);
      setPanel("relationships");
      setSelectedDeviceId(String(response.data.id));
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to create device.");
    } finally {
      setSaving(false);
    }
  }

  function toggleCapability(capability) {
    setTypeForm((current) => {
      const selected = current.default_capabilities.includes(capability.id);
      const default_capabilities = selected
        ? current.default_capabilities.filter((item) => item !== capability.id)
        : [...current.default_capabilities, capability.id];
      const default_effects = [
        ...new Set(
          capabilities
            .filter((item) => default_capabilities.includes(item.id))
            .flatMap((item) => item.effects.map((effect) => effect.id)),
        ),
      ];
      return { ...current, default_capabilities, default_effects };
    });
  }

  async function submitType(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const response = await createDeviceType(typeForm);
      setNotice(`${response.data.name} device type created.`);
      setTypeForm(emptyType);
      setDeviceForm((current) => ({
        ...current,
        device_type_id: String(response.data.id),
      }));
      setPanel("create");
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to create device type.");
    } finally {
      setSaving(false);
    }
  }

  async function submitRelationship(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await addRelationship(Number(selectedDeviceId), {
        target_type: targetType,
        target_id: Number(targetId),
        relationship_type: relationshipDefaults[targetType],
      });
      setNotice("Relationship added.");
      setTargetId("");
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to add relationship.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p>Loading assets...</p>;

  return (
    <main className="asset-framework">
      <div className="asset-framework__header">
        <div>
          <p className="scenario-eyebrow">Data-driven OT framework</p>
          <h1>Railroad OT Assets</h1>
          <p>
            Define reusable device types, create field assets, and connect them
            to operational territory without database edits.
          </p>
        </div>
        <div className="asset-framework__tabs">
          {[
            ["inventory", "Inventory"],
            ["create", "Create Device"],
            ["types", "Device Types"],
            ["relationships", "Relationships"],
          ].map(([id, label]) => (
            <button
              className={panel === id ? "active" : ""}
              key={id}
              onClick={() => setPanel(id)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="scenario-error">{String(error)}</div>}
      {notice && <div className="asset-framework__notice">{notice}</div>}

      {panel === "inventory" && <DeviceInventory devices={devices} />}

      {panel === "create" && (
        <form className="asset-form" onSubmit={submitDevice}>
          <div className="asset-form__intro">
            <h2>Create custom OT device</h2>
            <p>
              Capabilities and supported effects inherit from the selected type.
            </p>
          </div>
          <div className="asset-form__grid">
            <label>
              Name
              <input name="name" required value={deviceForm.name} onChange={changeDevice} />
            </label>
            <label>
              Device Type
              <select
                name="device_type_id"
                required
                value={deviceForm.device_type_id}
                onChange={changeDevice}
              >
                <option value="">Select a type</option>
                {deviceTypes.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            {["vendor", "model", "firmware", "location", "subdivision", "track"].map(
              (field) => (
                <label key={field}>
                  {field[0].toUpperCase() + field.slice(1)}
                  <input
                    name={field}
                    required
                    value={deviceForm[field]}
                    onChange={changeDevice}
                  />
                </label>
              ),
            )}
            <label>
              Latitude
              <input name="latitude" type="number" step="any" value={deviceForm.latitude} onChange={changeDevice} />
            </label>
            <label>
              Longitude
              <input name="longitude" type="number" step="any" value={deviceForm.longitude} onChange={changeDevice} />
            </label>
            <label>
              Criticality
              <select name="criticality" value={deviceForm.criticality} onChange={changeDevice}>
                {["Low", "Medium", "High", "Critical"].map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
            <label className="asset-form__wide">
              Description
              <textarea name="description" required value={deviceForm.description} onChange={changeDevice} />
            </label>
          </div>
          {selectedType && (
            <div className="asset-form__inheritance">
              <strong>Inherited capabilities</strong>
              <span>{selectedType.default_capabilities.join(" · ") || "None configured"}</span>
            </div>
          )}
          <button className="launch-scenario-button" disabled={saving}>
            {saving ? "Creating…" : "Create Device"}
          </button>
        </form>
      )}

      {panel === "types" && (
        <form className="asset-form" onSubmit={submitType}>
          <div className="asset-form__intro">
            <h2>Define a device type</h2>
            <p>Capabilities automatically expose compatible attack effects.</p>
          </div>
          <div className="asset-form__grid">
            {["name", "category", "vendor", "model", "firmware_supported"].map(
              (field) => (
                <label key={field}>
                  {field.replace("_", " ").replace(/\b\w/g, (char) => char.toUpperCase())}
                  <input
                    required={field === "name"}
                    value={typeForm[field]}
                    onChange={(event) =>
                      setTypeForm((current) => ({
                        ...current,
                        [field]: event.target.value,
                      }))
                    }
                  />
                </label>
              ),
            )}
            <label className="asset-form__wide">
              Description
              <textarea
                value={typeForm.description}
                onChange={(event) =>
                  setTypeForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
              />
            </label>
          </div>
          <fieldset className="capability-picker">
            <legend>Capabilities</legend>
            {capabilities.map((capability) => (
              <label key={capability.id}>
                <input
                  type="checkbox"
                  checked={typeForm.default_capabilities.includes(capability.id)}
                  onChange={() => toggleCapability(capability)}
                />
                <span>
                  <strong>{capability.label}</strong>
                  <small>
                    {capability.effects.map((effect) => effect.label).join(", ")}
                  </small>
                </span>
              </label>
            ))}
          </fieldset>
          <button className="launch-scenario-button" disabled={saving}>
            {saving ? "Saving…" : "Create Device Type"}
          </button>
        </form>
      )}

      {panel === "relationships" && (
        <section className="asset-form">
          <div className="asset-form__intro">
            <h2>Relationship editor</h2>
            <p>Select a source device and assign operational assets.</p>
          </div>
          <form className="relationship-flow" onSubmit={submitRelationship}>
            <label>
              Source device
              <select required value={selectedDeviceId} onChange={(event) => setSelectedDeviceId(event.target.value)}>
                <option value="">Select device</option>
                {devices.map((device) => (
                  <option key={device.id} value={device.id}>{device.name}</option>
                ))}
              </select>
            </label>
            <span className="relationship-flow__arrow">→</span>
            <label>
              Target kind
              <select
                value={targetType}
                onChange={(event) => {
                  setTargetType(event.target.value);
                  setTargetId("");
                }}
              >
                <option value="TRACK_BLOCK">Track Block</option>
                <option value="TRACK_SWITCH">Switch</option>
                <option value="GRADE_CROSSING">Crossing</option>
                <option value="OT_DEVICE">OT Device</option>
              </select>
            </label>
            <span className="relationship-flow__arrow">→</span>
            <label>
              Target
              <select required value={targetId} onChange={(event) => setTargetId(event.target.value)}>
                <option value="">Select target</option>
                {(targets[targetType] ?? []).map((target) => (
                  <option key={target.id} value={target.id}>{target.name}</option>
                ))}
              </select>
            </label>
            <button disabled={saving}>Assign</button>
          </form>
          <div className="relationship-cards">
            {devices
              .filter((device) => device.relationships?.length)
              .map((device) => (
                <article key={device.id}>
                  <h3>{device.name}</h3>
                  <p>{device.dynamic_summary}</p>
                  <ul>
                    {device.relationships.map((relationship) => (
                      <li key={relationship.id}>
                        {relationship.relationship_type.replaceAll("_", " ")} →{" "}
                        {relationship.target_name}
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
          </div>
        </section>
      )}
    </main>
  );
}

export default Assets;
