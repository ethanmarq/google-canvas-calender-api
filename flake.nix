{
  description = "A Nix flake for syncing Canvas calendar to Google Calendar";

  inputs = {
    nixpkgs.url = "github:Nixos/nixpkgs/nixos-24.05";
  };

  outputs = { self, nixpkgs }:
    let
      # A helper to apply a function to each of the default systems supported by Nixpkgs
      forAllSystems = nixpkgs.lib.genAttrs nixpkgs.lib.systems.flakeExposed;

      # Define our Python package set once
      pythonPackages = ps: [
        ps.requests
        ps.google-api-python-client
        ps.google-auth-httplib2
        ps.google-auth-oauthlib
      ];
    in
    {
      # This structure builds `apps.<system>.default`, which is what Nix expects
      apps = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonEnv = pkgs.python3.withPackages pythonPackages;
        in
        {
          default = {
            type = "app";
            program = "${pkgs.writeShellScriptBin "run-sync" ''
              #!${pkgs.stdenv.shell}
              exec ${pythonEnv}/bin/python ${./calender_sync.py} "$@"
            ''}/bin/run-sync";
          };
        });

      # This defines the development shell
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = [
              (pkgs.python3.withPackages pythonPackages)
            ];
          };
        });
    };
}
