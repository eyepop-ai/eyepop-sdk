#!/usr/bin/env bash
# Reference the published EyePop.Sdk package from a scratch app and check Client.Version() equals the release tag's version.
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" nuget)

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"
cat >verify.csproj <<XML
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="EyePop.Sdk" Version="[$version]" />
  </ItemGroup>
</Project>
XML
echo 'Console.WriteLine(EyePop.Client.Version());' >Program.cs

# Restore only from nuget.org into an empty package directory, so a cached or local copy cannot pass.
export NUGET_PACKAGES="$scratch/packages"

# A fresh push is validated and indexed by nuget.org before it restores: minutes for a first version. Wait up to 10 minutes.
for attempt in $(seq 30); do
  dotnet restore --source https://api.nuget.org/v3/index.json --no-cache >restore.log 2>&1 && break
  [ "$attempt" -lt 30 ] || { cat restore.log >&2; echo "cannot restore EyePop.Sdk $version" >&2; exit 1; }
  sleep 20
done

got=$(dotnet run --no-restore)
[ "$got" = "$version" ] || { echo "got $got, want $version" >&2; exit 1; }
echo "ok EyePop.Sdk $got"
