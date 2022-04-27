#!/bin/bash
#SBATCH --job-name=jupyterhub
#SBATCH --chdir={{homedir}}
#SBATCH --export={{keepvars}}
#SBATCH --get-user-env=L
#SBATCH --partition={{partition}}
{% if runtime    %}#SBATCH --time={{runtime}}
{% endif %}{% if gres       %}#SBATCH --gres={{gres}}
{% endif %}{% if nprocs     %}#SBATCH --cpus-per-task={{nprocs}}
{% endif %}{% if mem        %}#SBATCH --mem={{mem}}
{% endif %}{% if reservation%}#SBATCH --reservation={{reservation}}
{% endif %}{% if exclusive  %}#SBATCH --exclusive
{% endif %}{% if not output %}#SBATCH --output=/dev/null
{% endif %}{% if options %}#SBATCH {{options}}
{% endif %}

set -euo pipefail

trap 'echo SIGTERM received' TERM
{{prologue}}
{{cmd}}
