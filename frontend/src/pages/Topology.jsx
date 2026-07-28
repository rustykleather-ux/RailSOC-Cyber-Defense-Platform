import NetworkTopology from "../components/NetworkTopology";

function Topology({ devices, trackBlocks }) {
  return (
    <NetworkTopology
      devices={devices}
      trackBlocks={trackBlocks}
    />
  );
}

export default Topology;
