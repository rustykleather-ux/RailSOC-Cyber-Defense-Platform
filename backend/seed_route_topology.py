from models import RouteTopologySegment, TrackBlock, TrackSwitch


def seed_route_topology(db):
    """Seed explicit bidirectional adjacency for the demonstration territory."""
    blocks = db.query(TrackBlock).order_by(
        TrackBlock.subdivision,
        TrackBlock.track,
        TrackBlock.start_milepost,
    ).all()
    track_switch = db.query(TrackSwitch).filter(
        TrackSwitch.name == "Switch E86"
    ).first()
    created = []
    by_territory = {}
    for block in blocks:
        by_territory.setdefault((block.subdivision, block.track), []).append(block)

    for territory_blocks in by_territory.values():
        for left, right in zip(territory_blocks, territory_blocks[1:]):
            for source, destination in ((left, right), (right, left)):
                segment = db.query(RouteTopologySegment).filter(
                    RouteTopologySegment.from_block_id == source.id,
                    RouteTopologySegment.to_block_id == destination.id,
                ).first()
                switch_required = bool(
                    track_switch
                    and {left.id, right.id}
                    == {track_switch.track_block_id, right.id}
                    and float(track_switch.milepost) == float(left.end_milepost)
                )
                if segment is None:
                    segment = RouteTopologySegment(
                        name=f"{source.name} to {destination.name}",
                        from_block_id=source.id,
                        to_block_id=destination.id,
                        signal_block_id=destination.id,
                        required_signal_aspect="Clear",
                        switch_id=track_switch.id if switch_required else None,
                        required_switch_position="Normal" if switch_required else None,
                        enabled=True,
                    )
                    db.add(segment)
                created.append(segment)
    db.flush()
    return created
