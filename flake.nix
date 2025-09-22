{
  description = "A Nix flake for syncing Canvas calendar to Google Calendar";

  inputs = {
    nixpkgs.url = "github:Nixos/nixpkgs/nixos-24.05";
  };

  outputs = { self, nixpkgs }:
    let
      # Support multiple systems
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forEachSupportedSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
        pkgs = import nixpkgs { inherit system; };
      });
    in
    forEachSupportedSystem ({ pkgs }:
      let
        # Define the Python environment with required packages
        pythonEnv = pkgs.python3.withPackages (ps: [
          ps.requests
          ps.google-api-python-client
          ps.google-auth-httplib2
          ps.google-auth-oauthlib
        ]);
      in
      {
        # The `nix run` command will execute this app
        apps.default = {
          type = "app";
          program = "${pkgs.writeShellScriptBin "canvas-google-sync" ''
            #!${pkgs.stdenv.shell}
            # This wrapper ensures the script runs with the correct Python interpreter and packages
            exec "${pythonEnv}/bin/python" "${./canvas_google_sync.py}" "$@"
          ''}/bin/canvas-google-sync";
        };

        # A development shell available via `nix develop`
        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
          ];
        };
      });
}
