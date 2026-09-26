local mod = get_mod("DepthsPreview")

return {
  name = mod:localize("mod_name"),
  description = mod:localize("mod_description"),
  is_togglable = false,
  options = {
    widgets = {},
  },
}
