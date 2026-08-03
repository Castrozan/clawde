{
  lib,
}:
let
  resolve =
    selected: harness:
    let
      harnessCanEmbedDiscord = harness != null && lib.elem "discord" harness.embeddedChannelTypes;
      harnessCanBridgeDiscord = harness != null && harness.buildOneShotTurnCommandFor != null;
    in
    if selected == "embedded" then
      {
        transport = if harnessCanEmbedDiscord then "embedded" else "none";
        satisfiable = harnessCanEmbedDiscord;
      }
    else if selected == "sidecar" then
      {
        transport = if harnessCanBridgeDiscord then "sidecar" else "none";
        satisfiable = harnessCanBridgeDiscord;
      }
    else if harnessCanEmbedDiscord then
      {
        transport = "embedded";
        satisfiable = true;
      }
    else if harnessCanBridgeDiscord then
      {
        transport = "sidecar";
        satisfiable = true;
      }
    else
      {
        transport = "none";
        satisfiable = false;
      };
in
{
  inherit resolve;
}
