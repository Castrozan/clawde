{
  lib,
  assertion,
  stringify,
}:
let
  transportResolution = import ../../lib/discord-transport.nix { inherit lib; };

  fakeEmbeddingHarness = {
    embeddedChannelTypes = [
      "none"
      "discord"
    ];
    buildOneShotTurnCommandFor = null;
  };
  fakeBridgingHarness = {
    embeddedChannelTypes = [ "none" ];
    buildOneShotTurnCommandFor = "true";
  };
  fakePassiveHarness = {
    embeddedChannelTypes = [ "none" ];
    buildOneShotTurnCommandFor = null;
  };

  resolvedTransportFor = selected: harness: (transportResolution.resolve selected harness).transport;

  transportAssertion =
    name: expected: selected: harness:
    assertion name expected (resolvedTransportFor selected harness);

  satisfiableFor =
    selected: harness: stringify (transportResolution.resolve selected harness).satisfiable;

  satisfiableAssertion =
    name: expected: selected: harness:
    assertion name expected (satisfiableFor selected harness);
in
{
  inherit
    resolvedTransportFor
    transportAssertion
    satisfiableFor
    satisfiableAssertion
    fakeEmbeddingHarness
    fakeBridgingHarness
    fakePassiveHarness
    ;
}
