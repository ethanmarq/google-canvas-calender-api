{
  description = "A Nix flake for syncing Canvas calendar to Google Calendar";

  inputs = {
    nixpkgs.url = "github:Nixos/nixpkgs/nixos-24.05";
  };

  outputs = { self, nixpkgs }:
    # This helper function applies the configuration to each supported system
    nixpkgs.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Define the Python environment with required packages
        pythonEnv = pkgs.python3.withPackages (ps: [
          ps.requests
          ps.google-api-python-client
          ps.google-auth-httplib2
          ps.google-auth-oauthlib
        ]);
      in
      {
        # The `nix run .` command will execute this app
        apps.default = {
          type = "app";
          program = "${pkgs.writeShellScriptBin "run-sync" ''
            #!${pkgs.stdenv.shell}
            # This wrapper runs the python script from the current directory
            exec ${pythonEnv}/bin/python ${./calender_sync.py} "$@"
          ''}/bin/run-sync";
        };

        # A development shell available via `nix develop`
        devShells.default = pkgs.mkShell {
          packages = [ pythonEnv ];
        };
      });
}
