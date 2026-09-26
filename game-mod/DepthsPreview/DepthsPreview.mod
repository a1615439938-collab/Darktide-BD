return {
  run = function()
    fassert(rawget(_G, "new_mod"), "`DepthsPreview` requires the Darktide Mod Framework.")

    new_mod("DepthsPreview", {
      mod_script       = "DepthsPreview/scripts/mods/DepthsPreview/DepthsPreview",
      mod_data         = "DepthsPreview/scripts/mods/DepthsPreview/DepthsPreview_data",
      mod_localization = "DepthsPreview/scripts/mods/DepthsPreview/DepthsPreview_localization",
    })
  end,
  packages = {},
}
