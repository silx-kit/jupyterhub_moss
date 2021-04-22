function resetSpawnForm() {
  document.getElementById('spawn_form').reset();
  setSimplePartition(window.SLURM_DATA.default_partition);
}

function setSimplePartition(name) {
  const partitionElem = document.getElementById('partition');
  const gpuDivSimple = document.getElementById('gpu_simple');
  const gpuRadio0Simple = document.getElementById('0Gpu');
  const ngpusElem = document.getElementById('ngpus');
  const mediumCpuFieldSimple = document.getElementById('mediumCpufield');
  const mediumCoreSimple = document.getElementById('mediumCore');
  const maximumCpuFieldSimple = document.getElementById('maximumCpufield');
  const maximumCoreSimple = document.getElementById('maximumCore');
  const nprocsElem = document.getElementById('nprocs');

  partitionElem.value = name;
  updatePartitionLimits();

  const info = window.SLURM_DATA.partitions[name];

  // Toggle GPU choice display
  if (info.max_ngpus !== 0) {
    gpuDivSimple.removeAttribute('hidden');
  } else {
    gpuDivSimple.setAttribute('hidden', '');
  }

  // Reset ngpus and GPUs choice
  gpuRadio0Simple.checked = true;
  ngpusElem.value = "0";

  // Update displayed NProcs info and values
  // Get number of CPUs for given paritition choice
  const maxNProcs = info.max_nprocs;
  const halfNProcs = Math.floor(maxNProcs / 2);

  mediumCpuFieldSimple.textContent = `${halfNProcs} cores`;
  mediumCoreSimple.value = halfNProcs;
  maximumCpuFieldSimple.textContent = `${maxNProcs} cores`;
  maximumCoreSimple.value = maxNProcs;

  // Update nprocs according to current CPUs choice
  const selector = document.querySelector('input[name="nprocs_simple"]:checked');
  nprocsElem.value = selector ? selector.value : '1';
}

function updatePartitionLimits() {
  const nnodesElem = document.getElementById("nnodes");
  const nprocsElem = document.getElementById("nprocs");
  const ngpusElem = document.getElementById("ngpus");

  const partition = document.getElementById('partition').value;
  const info = window.SLURM_DATA.partitions[partition];

  if (nnodesElem.value > info.max_nnodes) nnodesElem.value = info.max_nnodes;
  nnodesElem.max = info.max_nnodes;

  if (nprocsElem.value > info.max_nprocs) nprocsElem.value = info.max_nprocs;
  nprocsElem.max = info.max_nprocs;

  if (ngpusElem.value > info.max_ngpus) ngpusElem.value = info.max_ngpus;
  ngpusElem.max = info.max_ngpus;
  ngpusElem.disabled = info.max_ngpus === 0;

  document.querySelectorAll('input[name="ngpus_simple"]').forEach(element =>
  {
    const labelElem = document.querySelector(`label[for="${element.id}"]`)
    if (element.value <= info.max_ngpus) {
      element.removeAttribute('hidden');
      labelElem.removeAttribute('hidden');
    } else {
      element.setAttribute('hidden', '');
      labelElem.setAttribute('hidden', '');
    }
  });
}

// Handle document ready
document.addEventListener("DOMContentLoaded", () => {
  resetSpawnForm();  // Init

  const nprocs = document.getElementById('nprocs');
  const exclusive = document.getElementById('exclusive');
  const ngpus = document.getElementById('ngpus');
  const jupyterlab = document.getElementById('jupyterlab');
  const runtime = document.getElementById('runtime');

  // Update advanced form from Simple tab inputs
  // Partitions
  document.querySelectorAll('input[name="partition_simple"]').forEach(element => {
    element.addEventListener('change', e => {
      setSimplePartition(e.target.value);
    });
  });
  // CPUs
  document.querySelectorAll('input[name="nprocs_simple"]').forEach(element => {
    element.addEventListener('change', e => {
      nprocs.value = e.target.value;
      exclusive.checked = e.target.id === 'maximumCore';
    });
  });
  // GPUs
  document.querySelectorAll('input[name="ngpus_simple"]').forEach(element => {
    element.addEventListener('change', e => {
      ngpus.value = e.target.value;
    });
  });
  // JupyterLab
  document.getElementById('jupyterlab_simple').addEventListener(
    'change', e => {
      jupyterlab.checked = e.target.checked;
  });
  // Runtime
  document.getElementById('runtime_simple').addEventListener(
    'change', e => {
      runtime.value = e.target.value;
  });

  // Reset when returning to simple tab
  document.getElementById('simple_tab_link').addEventListener(
    'click', resetSpawnForm
  );

  // Update limits when partition is changed
  document.getElementById('partition').addEventListener(
    'change', updatePartitionLimits
  );

});
