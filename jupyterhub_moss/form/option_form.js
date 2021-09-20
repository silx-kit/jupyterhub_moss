const CONFIG_NAME = 'form-config:v1';

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
    runtimeSelect.dispatchEvent(new Event('change'));
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

function storeConfigToLocalStorage() {
  const advancedDiv = document.getElementById("menu1");
  const runtimeSelect = document.getElementById('runtime_simple');

  // Retrieve form fields to store
  const fieldNames = ['partition', 'nprocs', 'ngpus', 'runtime', 'jupyterlab',
                      'exclusive', 'reservation', 'nnodes', 'ntasks', 'options'];
  const fields = {}
  for (const name of fieldNames) {
    const elem = document.getElementById(name);
    if (elem.type && elem.type === 'checkbox') {
      fields[name] = elem.checked;
    } else {
      fields[name] = elem.value;
    }
  }

  // Persist simple inputs
  window.localStorage.setItem(CONFIG_NAME, JSON.stringify({
    'isAdvanced': advancedDiv !== null && advancedDiv.classList.contains('active'),
    'simple': {
      'partitionId': document.querySelector('input[name="partition_simple"]:checked').id,
      'nprocsId': document.querySelector('input[name="nprocs_simple"]:checked').id,
      'ngpusId': document.querySelector('input[name="ngpus_simple"]:checked').id,
      'runtime': runtimeSelect.value,
    },
    'fields': fields,
  }));
}

function restoreConfigFromLocalStorage() {
  const advancedLink = document.getElementById("advanced_tab_link");
  const jupyterlabSimpleElem = document.getElementById('jupyterlab_simple');
  const runtimeSelect = document.getElementById('runtime_simple');

  resetSpawnForm();

  // Load config
  const config = JSON.parse(window.localStorage.getItem(CONFIG_NAME));
  if (config === null) {
    return;
  }

  if (config['isAdvanced']) { // Restore advanced tab
    advancedLink.click();

    const fields = config['fields'];
    for (const name in fields) {
      const elem = document.getElementById(name);
      const value = fields[name];
      if (typeof value === "boolean") {
        elem.checked = value;
      } else {
        elem.value = value;
      }
      elem.dispatchEvent(new Event('change'));
    }

  } else { // Restore simple tab
    for (const key of ['partitionId', 'nprocsId', 'ngpusId']) {
      const element = document.getElementById(config['simple'][key]);
      if (element !== null) {
        element.checked = true;
        element.dispatchEvent(new Event('change'));
      }
    }
    runtimeSelect.value = config['simple']['runtime'];
    runtimeSelect.dispatchEvent(new Event('change'));
    jupyterlabSimpleElem.checked = config['fields']['jupyterlab'];
    jupyterlabSimpleElem.dispatchEvent(new Event('change'));
  }
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
    'submit', (e) => storeConfigToLocalStorage()
  );

  restoreConfigFromLocalStorage();
});
