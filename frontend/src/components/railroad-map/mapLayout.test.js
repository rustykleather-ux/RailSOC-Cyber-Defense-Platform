import assert from "node:assert/strict";
import test from "node:test";
import {
  blockState,
  controlledAssetKeys,
  dispatchCommandState,
  mapDimensions,
  matchesFilters,
  milepostToX,
  trainState,
} from "./mapLayout.js";

test("map exposes pending, queued, completed, and blocked command state", () => {
  for (const status of ["Pending", "Queued", "Completed", "Blocked"]) {
    assert.equal(
      dispatchCommandState(
        [{ target_type: "TRAIN", target_id: 7, status }],
        "TRAIN",
        7,
      ),
      status.toLowerCase(),
    );
  }
  assert.equal(dispatchCommandState([], "TRAIN", 7), "");
});

test("milepost layout is proportional and supports variable subdivision spans", () => {
  const x80 = milepostToX(80, 80, 100, 1200);
  const x90 = milepostToX(90, 80, 100, 1200);
  const x100 = milepostToX(100, 80, 100, 1200);
  assert.equal(x90 - x80, x100 - x90);

  const dimensions = mapDimensions([
    {
      name: "East",
      minimum_milepost: 80,
      maximum_milepost: 100,
      tracks: ["Main", "Siding"],
    },
    {
      name: "West",
      minimum_milepost: 10,
      maximum_milepost: 15,
      tracks: ["Main"],
    },
  ]);
  assert.equal(dimensions.corridors.length, 2);
  assert.ok(dimensions.corridors[1].top > dimensions.corridors[0].top);
  assert.notEqual(
    dimensions.corridors[0].trackY.Main,
    dimensions.corridors[0].trackY.Siding,
  );
});

test("block visual priority puts cyber and communications before operations", () => {
  const base = {
    occupied: true,
    maintenance: true,
    signal_aspect: "Stop",
    communications_status: "Degraded",
    security_status: "Compromised",
  };
  assert.equal(blockState(base), "security");
  assert.equal(blockState({ ...base, security_status: "Healthy" }), "communications");
  assert.equal(
    blockState({
      ...base,
      security_status: "Healthy",
      communications_status: "Online",
    }),
    "maintenance",
  );
  assert.equal(
    blockState({
      ...base,
      security_status: "Healthy",
      communications_status: "Online",
      maintenance: false,
    }),
    "stop",
  );
});

test("train states distinguish stops and PTC restrictions", () => {
  assert.equal(trainState({ status: "Stopped at Signal", speed: 0 }), "stopped");
  assert.equal(
    trainState({
      status: "Restricted - PTC Communications",
      speed: 20,
    }),
    "ptc",
  );
  assert.equal(trainState({ status: "Moving", speed: 40 }), "moving");
});

test("device relationships identify controlled assets for highlighting", () => {
  const keys = controlledAssetKeys({
    relationships: [
      { target_type: "TRACK_BLOCK", target_id: 2 },
      { target_type: "TRACK_BLOCK", target_id: 3 },
      { target_type: "TRACK_SWITCH", target_id: 7 },
    ],
  });
  assert.deepEqual(keys, [
    "TRACK_BLOCK:2",
    "TRACK_BLOCK:3",
    "TRACK_SWITCH:7",
  ]);
});

test("map filters hide assets outside selected subdivision, track, and state", () => {
  const block = {
    type: "block",
    subdivision: "East",
    track: "Main",
    signal_aspect: "Clear",
    occupied: false,
    maintenance: false,
    security_status: "Healthy",
    communications_status: "Online",
  };
  const filters = {
    subdivision: "East",
    track: "Main",
    operational: "normal",
    security: "healthy",
    communications: "online",
  };
  assert.equal(matchesFilters(block, filters), true);
  assert.equal(
    matchesFilters(block, { ...filters, subdivision: "West" }),
    false,
  );
  assert.equal(
    matchesFilters(block, { ...filters, track: "Siding" }),
    false,
  );
  assert.equal(
    matchesFilters(
      { ...block, security_status: "Compromised" },
      filters,
    ),
    false,
  );
});
