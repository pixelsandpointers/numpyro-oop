{
  # A short description of this flake project
  description = "Workshop example flake";

  # Declare flake inputs (external dependencies)
  inputs = {
    # Schema validator for flake structure (optional but good for tooling)
    flake-schemas.url = "https://flakehub.com/f/DeterminateSystems/flake-schemas/*";

    # Pull in the nixpkgs package set (source of all packages)
    nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/*";
  };

  # The actual outputs of the flake
  outputs = { self, flake-schemas, nixpkgs }:

    let
      # Define which systems this flake should support
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      # Helper function: generate outputs for each system using `genAttrs`
      forEachSupportedSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
        pkgs = import nixpkgs { inherit system; };
      });
    in
    {
      # Optional schema declaration (used by flake-aware tools for validation)
      schemas = flake-schemas.schemas;

      # Define runnable shell applications (e.g. `nix run`)
      packages = forEachSupportedSystem ({ pkgs }: {
        default = pkgs.writeShellApplication {
          name = "run";

          # Runtime dependencies for the script to run correctly
          runtimeInputs = with pkgs; [ uv python312 stdenv.cc.cc.lib ];

          # Script contents (will be in the PATH and executable)
          text = ''
            # Fix for missing libstdc++.so.6 at runtime
            export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib

            # Run your Python script using uv (Python package runner)
            uv run python ./examples/script.py
          '';
        };
      });

      # Define devShells for interactive use (e.g. `nix develop`)
      devShells = forEachSupportedSystem ({ pkgs }: {
        default = pkgs.mkShell {
          # Tools and packages available in the shell
          packages = with pkgs; [
            python312
            uv
            curl
            git
            jq
            wget
            nixpkgs-fmt
          ];

          # Export linker path so Python can find libstdc++.so.6
          shellHook = ''
            export LD_LIBRARY_PATH={pkgs.stdenv.cc.cc.lib}/lib
            echo "Hello from Nix"
          '';
        };
      });
    };
}
