const CONFIG_SIMPLE_NAME = 'config:simple';

function resetSpawnForm() {
  document.getElementById('spawn_form').reset();
  setSimplePartition(window.SLURM_DATA.default_partition);
}

function setVisible(element, visible) {
  if (visible) {
    element.removeAttribute('hidden');
  } else {
    element.setAttribute('hidden', '');
  }
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
  const runtimeSelect = document.getElementById('runtime_simple');

  if (!window.SLURM_DATA.partitions.hasOwnProperty(name)) {
    return; // Not a supported partition
  }

  partitionElem.value = name;
  updatePartitionLimits();

  const info = window.SLURM_DATA.partitions[name];

  // Toggle GPU choice display
  setVisible(gpuDivSimple, info.max_ngpus !== 0);

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

  // Update available runtime options
  // Reset to 1 hour if choice is not available with current partition
  if (runtimeSelect.value * 3600 > info['max_runtime']) {
    runtimeSelect.selectedIndex = 0;
  };
  for (i=0; i<runtimeSelect.options.length; i++) {
    const element = runtimeSelect.options[i];
    setVisible(element, element.value * 3600 <= info['max_runtime']);
  };
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
    const isVisible = element.value <= info.max_ngpus;
    setVisible(element, isVisible);
    setVisible(document.querySelector(`label[for="${element.id}"]`), isVisible);
  });
}

function saveSimpleConfigToLocalStorage() {
  // Persist simple inputs
  window.localStorage.setItem(CONFIG_SIMPLE_NAME, JSON.stringify({
    'version': 1,
    'partitionId': document.querySelector('input[name="partition_simple"]:checked').id,
    'nprocsId': document.querySelector('input[name="nprocs_simple"]:checked').id,
    'ngpusId': document.querySelector('input[name="ngpus_simple"]:checked').id,
    'jupyterlab': document.getElementById('jupyterlab_simple').checked,
    'runtime': document.getElementById('runtime_simple').value,
  }));
}

function loadSimpleConfigFromLocalStorage() {
  const jupyterlabSimpleElem = document.getElementById('jupyterlab_simple');
  const runtimeSimpleElem = document.getElementById('runtime_simple');

  // Load config
  const configString = window.localStorage.getItem(CONFIG_SIMPLE_NAME);
  if (configString === null) {
    return;
  }
  const config = JSON.parse(configString);
  if (!config.hasOwnProperty('version') || config['version'] !== 1) {
    return;
  }

  ['partitionId', 'nprocsId', 'ngpusId'].forEach(
    (key) => {
      const element = document.getElementById(config[key]);
      if (element !== null) {
        element.checked = true;
        element.dispatchEvent(new Event('change'));
      }
    }
  );
  jupyterlabSimpleElem.checked = config['jupyterlab'];
  jupyterlabSimpleElem.dispatchEvent(new Event('change'));
  runtimeSimpleElem.value = config['runtime'];
  runtimeSimpleElem.dispatchEvent(new Event('change'));
}

// Handle document ready
document.addEventListener("DOMContentLoaded", () => {
  resetSpawnForm();  // Init

  const nprocsElem = document.getElementById('nprocs');
  const exclusiveElem = document.getElementById('exclusive');
  const ngpusElem = document.getElementById('ngpus');
  const jupyterlabElem = document.getElementById('jupyterlab');
  const runtimeElem = document.getElementById('runtime');

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
      nprocsElem.value = e.target.value;
      exclusiveElem.checked = e.target.id === 'maximumCore';
    });
  });
  // GPUs
  document.querySelectorAll('input[name="ngpus_simple"]').forEach(element => {
    element.addEventListener('change', e => {
      ngpusElem.value = e.target.value;
    });
  });
  // JupyterLab
  document.getElementById('jupyterlab_simple').addEventListener(
    'change', e => {
      jupyterlabElem.checked = e.target.checked;
  });
  // Runtime
  document.getElementById('runtime_simple').addEventListener(
    'change', e => {
      runtimeElem.value = `${e.target.value}:00:00`;
  });

  // Reset when returning to simple tab
  document.getElementById('simple_tab_link').addEventListener(
    'click', resetSpawnForm
  );

  // Update limits when partition is changed
  document.getElementById('partition').addEventListener(
    'change', updatePartitionLimits
  );

  // Catch form submit
  document.getElementById('spawn_form').addEventListener(
    'submit', (e) => {
      const simpleDiv = document.getElementById("home");
      if (simpleDiv !== null && simpleDiv.classList.contains('active')) {
        saveSimpleConfigToLocalStorage();
      }
    }
  );

  loadSimpleConfigFromLocalStorage();
});
