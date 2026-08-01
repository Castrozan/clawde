{
  lib,
  ...
}:
{
  options.clawde.agents = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule {
        options.expose = lib.mkOption {
          type = lib.types.submodule {
            options = {
              a2a = lib.mkOption {
                type = lib.types.submodule {
                  options = {
                    enable = lib.mkOption {
                      type = lib.types.bool;
                      default = false;
                      description = "Expose this agent as an A2A peer over HTTP. The supervisor runs the a2a-server as a headless sidecar process beside the agent, attached to whichever multiplexer hosts it, so the agent's own window stays the single thing a human opens.";
                    };
                    listenHost = lib.mkOption {
                      type = lib.types.str;
                      default = "127.0.0.1";
                      description = "Bind host for the A2A HTTP server. The transport has zero built-in auth; binding to 0.0.0.0 exposes the agent to anyone who can reach the LAN. Front any non-loopback bind with a reverse proxy that adds authentication.";
                    };
                    listenPort = lib.mkOption {
                      type = lib.types.int;
                      default = 7001;
                      description = "Bind port for the A2A HTTP server. Must be unique across all clawde agents.";
                    };
                    publicEndpointUrl = lib.mkOption {
                      type = lib.types.nullOr lib.types.str;
                      default = null;
                      description = "URL advertised in the Agent Card. Null derives http://<listenHost>:<listenPort>.";
                    };
                    agentDescriptionForCard = lib.mkOption {
                      type = lib.types.str;
                      default = "";
                      description = "Free-form description published in the Agent Card. Defaults to the agent name when empty.";
                    };
                    meaningfulLinePattern = lib.mkOption {
                      type = lib.types.nullOr lib.types.str;
                      default = null;
                      description = "Regex matching the only pane lines that count as meaningful new output. Filters out status-line and spinner redraws so the a2a-server's idle auto-complete fires. Null inherits the harness's own response-marker pattern, which is the right answer unless the agent renders through something else.";
                    };
                  };
                };
                default = { };
                description = "A2A peer exposure configuration.";
              };
            };
          };
          default = { };
          description = "Interop adapters that expose this agent to non-channel consumers (other agents, scripts, services).";
        };
      }
    );
  };
}
