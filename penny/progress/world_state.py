"""Pure private world transitions; fixed baseline and virtual-only candidate IDs."""
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)
BASELINE = "preview-v1"
MAX_EVENTS = 2048
# These are provisional virtual item identifiers, not approved or rendered art.
DECOR = frozenset(("plant-v1", "mug-v1"))
OUTFITS = frozenset(("plum-outfit-v1",))
SLOTS = frozenset(("left-shelf", "right-shelf", "desk-corner"))
ACTIONS = frozenset(("acquire", "place", "move", "store", "equip", "unequip", "remove"))


@dataclass(frozen=True, slots=True)
class World:
    revision: int = 0
    owned: frozenset = frozenset()
    placements: tuple = ()
    outfit: str | None = None


def valid_command(action, asset_id, slot):
    return (type(action) is str and action in ACTIONS
            and type(asset_id) is str and asset_id in DECOR | OUTFITS
            and (slot is None or type(slot) is str and slot in SLOTS | {"outfit"})
            and (slot in SLOTS if action in ("place", "move") else
                 slot == "outfit" if action == "equip" else slot is None))


def apply(world, action, asset_id, slot):
    """Return new state only for an exact allowed transition; no mutation."""
    try:
        if not valid_command(action, asset_id, slot) or world.revision >= MAX_EVENTS:
            return None
        owned = set(world.owned)
        placed = dict(world.placements)
        outfit = world.outfit
        if action == "acquire":
            if asset_id in owned:
                return None
            owned.add(asset_id)
        elif asset_id not in owned:
            return None
        elif action in ("place", "move"):
            if (asset_id not in DECOR or slot in placed.values()
                    or (asset_id in placed) != (action == "move")):
                return None
            placed[asset_id] = slot
        elif action == "store":
            if asset_id not in placed:
                return None
            del placed[asset_id]
        elif action == "equip":
            if asset_id not in OUTFITS or outfit == asset_id:
                return None
            outfit = asset_id
        elif action == "unequip":
            if outfit != asset_id:
                return None
            outfit = None
        elif action == "remove":
            if asset_id in placed or outfit == asset_id:
                return None  # Explicitly store/unequip before relinquishing.
            owned.remove(asset_id)
        return World(world.revision + 1, frozenset(owned),
                     tuple(sorted(placed.items())), outfit)
    except Exception as exc:
        logger.error("World transition failed (%s)", type(exc).__name__)
        raise
