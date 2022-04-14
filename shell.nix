# shell.nix
{ pkgs ? import <nixpkgs> {} }:
let
  my-python = pkgs.python3;
  python-with-my-packages = my-python.withPackages (p: with p; [

  #TODO Missing webdriver-manager on nixos
    beautifulsoup4
    requests
    lxml
    httplib2
    selenium
    pdfkit
    # other python packages you want
  ]);
in
pkgs.mkShell {
  buildInputs = [
    python-with-my-packages
    pkgs.chromedriver
    pkgs.wkhtmltopdf
    # other dependencies
  ];
  shellHook = ''
    PYTHONPATH=${python-with-my-packages}/${python-with-my-packages.sitePackages}
    # maybe set more env-vars
  '';
}
