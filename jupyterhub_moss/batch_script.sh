#!/bin/bash
#SBATCH --job-name=spawner-jupyterhub
#SBATCH --chdir={{homedir}}
{% if not output %}#SBATCH --output=/dev/null
{% else %}#SBATCH --output={{homedir}}/jupyterhub_slurmspawner_%j.log
{% endif %}
#SBATCH --export={{keepvars}}
#SBATCH --get-user-env=L
#SBATCH --partition={{partition}}
{% if runtime    %}#SBATCH --time={{runtime}}
{% endif %}{% if gres       %}#SBATCH --gres={{gres}}
{% endif %}{% if nprocs     %}#SBATCH --cpus-per-task={{nprocs}}
{% endif %}{% if mem        %}#SBATCH --mem={{mem}}
{% endif %}{% if reservation%}#SBATCH --reservation={{reservation}}
{% endif %}{% if exclusive  %}#SBATCH --exclusive
{% endif %}{% if options %}#SBATCH {{options}}
{% endif %}

set -euo pipefail

trap 'echo SIGTERM received' TERM
{{prologue}}
{% if srun %}{{srun}} {% endif %}{{cmd}}
echo "JupyterLab server ended gracefully"
{{epilogue}}
