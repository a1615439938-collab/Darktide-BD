local mod = get_mod("DepthsPreview")

local Archetypes = require("scripts/settings/archetype/archetypes")
local ToughnessTemplates = require("scripts/settings/toughness/archetype_toughness_templates")

local Balance = {}
local originals = nil

local function capture()
  if originals then
    return
  end
  originals = {
    veteran_toughness = ToughnessTemplates.veteran.max,
    zealot_toughness = ToughnessTemplates.zealot.max,
    ogryn_toughness = ToughnessTemplates.ogryn.max,
    psyker_crit = Archetypes.psyker.base_critical_strike_chance,
  }
end

function Balance.apply()
  capture()

  -- Fatshark Depths of the Damned preview / follow-up values.
  ToughnessTemplates.veteran.max = 120
  ToughnessTemplates.zealot.max = 125
  ToughnessTemplates.ogryn.max = 125
  Archetypes.psyker.base_critical_strike_chance = 0.10
end

function Balance.restore()
  if not originals then
    return
  end
  ToughnessTemplates.veteran.max = originals.veteran_toughness
  ToughnessTemplates.zealot.max = originals.zealot_toughness
  ToughnessTemplates.ogryn.max = originals.ogryn_toughness
  Archetypes.psyker.base_critical_strike_chance = originals.psyker_crit
end

return Balance
