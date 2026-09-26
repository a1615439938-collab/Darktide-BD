local mod = get_mod("DepthsPreview")

return {
  name = mod:localize("mod_name"),
  description = mod:localize("mod_description"),
  is_togglable = false,
  options = {
    widgets = {
      {
        setting_id = "open_preview",
        type = "button",
        button_text = "open",
        function_name = "open_preview",
      },
      {
        setting_id = "toggle_preview",
        type = "button",
        button_text = "toggle",
        function_name = "toggle_preview",
      },
    },
  },
}
