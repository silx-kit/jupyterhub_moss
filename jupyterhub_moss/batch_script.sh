#!/bin/bash
#SBATCH --job-name=jupyterhub
#SBATCH --chdir={{homedir}}
#SBATCH --export={{keepvars}}
#SBATCH --get-user-env=L
#SBATCH --partition={{partition}}
{% if runtime    %}#SBATCH --time={{runtime}}
{% endif %}{% if gres       %}#SBATCH --gres={{gres}}
{% endif %}{% if nprocs     %}#SBATCH --cpus-per-task={{nprocs}}
{% endif %}{% if reservation%}#SBATCH --reservation={{reservation}}
{% endif %}{% if nnodes     %}#SBATCH --nodes={{nnodes}}
{% endif %}{% if ntasks     %}#SBATCH --ntasks-per-node={{ntasks}}
{% endif %}{% if exclusive  %}#SBATCH --exclusive
{% endif %}

set -euo pipefail

trap 'echo SIGTERM received' TERM

{{cmd}}
