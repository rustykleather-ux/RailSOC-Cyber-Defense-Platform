import { useEffect, useState } from "react";
import DeviceInventory from "../components/DeviceInventory";
import { getDevices } from "../services/deviceService";

function Assets() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDevices() {
      try {
        const data = await getDevices();
        setDevices(data);
      } catch (err) {
        console.error("Failed to load devices:", err);
        setError("Unable to load railroad assets.");
      } finally {
        setLoading(false);
      }
    }

    loadDevices();
  }, []);

  if (loading) {
    return <p>Loading assets...</p>;
  }

  if (error) {
    return <p>{error}</p>;
  }

  return <DeviceInventory devices={devices} />;
}

export default Assets;