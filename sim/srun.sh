#!/bin/bash
echo $1 $2 $3

if [ $1 = 'i' ]; then
  # srun --partition=main --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=2000 --time=12:00:00 --export=ALL --pty bash -i
  srun --partition=main --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=4000 --time=3:00:00 --export=ALL --pty bash -i
elif [ $1 = 'r' ]; then
  FILE='sim.py'
  NTASKS=1
  echo "#!/bin/bash
#SBATCH --partition=main             # Partition (job queue)
#SBATCH --job-name=$FILE
#SBATCH --nodes=$NTASKS              # Number of nodes you require
#SBATCH --ntasks=$NTASKS             # Total # of tasks across all nodes
#SBATCH --cpus-per-task=1            # Cores per task (>1 if multithread tasks)
#SBATCH --mem=8000                   # Real memory (RAM) required (MB)
#SBATCH --time=12:00:00              # Total run time limit (HH:MM:SS)
#SBATCH --export=ALL                 # Export your current env to the job env
#SBATCH --output=log/slurm.%N.%j.out
export MV2_ENABLE_AFFINITY=0
srun --mpi=pmi2 python3 $PWD/$FILE
  " > sbatch_script.sh

  rm log/*
  sbatch sbatch_script.sh
elif [ $1 = 'l' ]; then
  squeue -u mfa51
elif [ $1 = 'k' ]; then
  scancel --user=mfa51 # -n learning
else
  echo "Arg did not match!"
fi
