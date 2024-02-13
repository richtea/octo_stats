# Octopus Energy Tracking

This repo contains Jupyter notebooks and other code to extract and display stats for [Octopus
Energy](https://octopus.energy/) consumption and a [MyEnergi Zappi](https://www.myenergi.com/zappi-ev-charger) charger.

**NOTE** Before committing to this repo, add the [Git pre-commit hook](./pre-commit) by copying the `./pre-commit` file
into the `.git/hooks` subfolder (you may also need to run `chmod +x .git/hooks/pre-commit`). This hook prevents
committing Jupyter notebook outputs.
