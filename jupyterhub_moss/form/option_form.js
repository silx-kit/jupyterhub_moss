const CONFIG_NAME = 'form-config:v3';
const CUSTOM_ENV_CONFIG_NAME = 'custom-environment-config:v1';

function removeAllChildren(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function createEnvironmentDiv(key, description, path, modules, checked = false) {
  const div = document.createElement('div');
  div.classList.add('environment-div');

  const radio_id = `environment_radio_${key}`;
  const title = `Environment Name: ${description}`;

  // Store definitions in hidden inputs
  const path_input = document.createElement('input');
  path_input.setAttribute('type', 'hidden');
  path_input.setAttribute('class', 'environment_path');
  path_input.setAttribute('value', path);
  div.appendChild(path_input);
  const mods_input = document.createElement('input');
  mods_input.setAttribute('type', 'hidden');
  mods_input.setAttribute('class', 'environment_modules');
  mods_input.setAttribute('value', modules);
  div.appendChild(mods_input);

  const input = document.createElement('input');
  input.setAttribute('type', 'radio');
  input.setAttribute('id', radio_id);
  input.setAttribute('title', title);
  input.setAttribute('name', 'environment_id');
  input.setAttribute('value', key);

  input.addEventListener('change', updateEnvironmentAddNameRequired);
  if (checked) {
    input.setAttribute('checked', '');
  }
  div.appendChild(input);

  const label = document.createElement('label');
  label.setAttribute('for', radio_id);
  label.setAttribute('title', title);
  label.textContent = description;
  div.appendChild(label);

  return div;
}

function createEnvironmentSimpleCustomGroup() {
  const environmentSimpleCustom = document.getElementById(
    'environment_simple_custom'
  );

  if (environmentSimpleCustom == null) {
    // create option group for custom environments in simple menu
    const optgroup = document.createElement('optgroup');
    optgroup.id = 'environment_simple_custom';
    optgroup.label = 'Custom';
    optgroup.hidden = true;
    document.getElementById('environment_simple').appendChild(optgroup);
  }
}

function resetEnvironmentSelection() {
  const environmentsDiv = document.getElementById('jupyter_environments');
  const environmentSimpleSelect = document.getElementById('environment_simple');

  environmentsDiv.querySelector('input[type="radio"]').checked = true;
  environmentSimpleSelect.selectedIndex = 0;
}

function selectEnvironment(key) {
  const environmentsDiv = document.getElementById('jupyter_environments');
  const environmentSimpleSelect = document.getElementById('environment_simple');

  if (key !== null) {
    const keyInputs = Array.from(
      environmentsDiv.querySelectorAll('input[type="radio"]')
    );
    const index = keyInputs.findIndex((element) => element.value === key);
    if (index >= 0) {
      keyInputs[index].checked = true;
      keyPath = keyInputs[index].parentNode.querySelector('input.environment_path');
      document.getElementById('environment_path').value = keyPath ? keyPath.value : '';
      keyModules = keyInputs[index].parentNode.querySelector('input.environment_modules');
      document.getElementById('environment_modules').value = keyModules ? keyModules.value : '';
      environmentSimpleSelect.selectedIndex = index;
      return;
    }
  }
  resetEnvironmentSelection();
}

function getSelectedEnvironment() {
  const environmentsDiv = document.getElementById('jupyter_environments');

  // Get selected environment if any
  const selectedRadio = environmentsDiv.querySelector(
    'input[type="radio"]:checked'
  );
  return selectedRadio ? selectedRadio.value : null;
}

function addCustomEnvironment(key, description, path, modules, persist = true) {
  const customEnvironmentDiv = document.getElementById(
    'jupyter_environments_custom'
  );
  const environmentSimpleCustomOptGroup = document.getElementById(
    'environment_simple_custom'
  );

  const div = createEnvironmentDiv(key, description, path, modules);

  button = document.createElement('button');
  button.setAttribute('type', 'button');
  button.classList.add('environment-remove-button');
  button.setAttribute(
    'title',
    'Remove this environment from the custom environments'
  );
  button.setAttribute('value', key);
  button.innerHTML = '&#xff0d;';
  button.addEventListener('click', (e) =>
    removeCustomEnvironment(e.target.value)
  );
  div.appendChild(button);

  customEnvironmentDiv.appendChild(div);

  const option = document.createElement('option');
  option.text = description;
  option.value = key;
  environmentSimpleCustomOptGroup.appendChild(option);
  setVisible(environmentSimpleCustomOptGroup, true);

  if (persist) {
    storeCustomEnvironmentsToLocalStorage();
  }
}

function removeCustomEnvironment(key, persist = true) {
  const customEnvironmentDiv = document.getElementById(
    'jupyter_environments_custom'
  );
  const environmentSimpleCustomOptGroup = document.getElementById(
    'environment_simple_custom'
  );

  if (key === null) {
    return;
  }
  const option = environmentSimpleCustomOptGroup.querySelector(
    `option[value=${key}]`
  );
  if (option !== null) {
    if (option.selected) {
      resetEnvironmentSelection();
    }
    option.parentNode.removeChild(option);
  }
  const radioSelect = customEnvironmentDiv.querySelector(
    `input[type="radio"][value=${key}]`
  );
  if (radioSelect !== null) {
    const div = radioSelect.parentNode;
    if (radioSelect.checked) {
      resetEnvironmentSelection();
    }
    div.parentNode.removeChild(div);
  }

  if (Object.keys(getCustomEnvironments()).length === 0) {
    setVisible(environmentSimpleCustomOptGroup, false);
  }

  if (persist) {
    storeCustomEnvironmentsToLocalStorage();
  }
}

function getCustomEnvironments() {
  const customEnvironmentDiv = document.getElementById(
    'jupyter_environments_custom'
  );

  const customEnvs = {};

  // Get key from radio button, description from label and definitons in hidden input
  customEnvironmentDiv.querySelectorAll('.environment-div').forEach((div) => {
    customEnvs[div.querySelector('input[type=radio]').value] = {
      description: div.querySelector('label').textContent,
      path: div.querySelector('input.environment_path').value,
      modules: div.querySelector('input.environment_modules').value,
    };
  });
  return customEnvs;
}

function storeCustomEnvironmentsToLocalStorage() {
  window.localStorage.setItem(
    CUSTOM_ENV_CONFIG_NAME,
    JSON.stringify(getCustomEnvironments())
  );
}

function restoreCustomEnvironmentsFromLocalStorage() {
  const customEnvironmentDiv = document.getElementById(
    'jupyter_environments_custom'
  );
  const environmentSimpleCustomOptGroup = document.getElementById(
    'environment_simple_custom'
  );

  // Remove previous custom environments
  resetEnvironmentSelection();
  removeAllChildren(customEnvironmentDiv);
  removeAllChildren(environmentSimpleCustomOptGroup);

  const config = JSON.parse(
    window.localStorage.getItem(CUSTOM_ENV_CONFIG_NAME)
  );
  if (config === null) {
    return;
  }

  for (const key in config) {
    addCustomEnvironment(key, config[key].description, config[key].path, config[key].modules, false);
  }
}

function updateDefaultEnvironments() {
  const defaultEnvironmentsDiv = document.getElementById(
    'jupyter_environments_default'
  );
  const environmentSimple = document.getElementById(
    'environment_simple'
  );

  const selectedKey = getSelectedEnvironment();

  document.querySelectorAll('.default-environment').forEach((defaultEnv) => {
    defaultEnv.querySelectorAll('div').forEach((envDiv) => {
      envDiv.parentNode.removeChild(envDiv);
    });
    defaultEnv.querySelectorAll('option').forEach((envOpt) => {
      envOpt.parentNode.removeChild(envOpt);
    });
  });

  const partition = document.getElementById('partition').value;
  const partitionInfo = window.SLURM_DATA.partitions[partition];

  // Populate default partition environments
  for (const key in partitionInfo.jupyter_environments) {
    const info = partitionInfo.jupyter_environments[key];
    const group_id = info.group ? info.group.replace(/\W/g, '_') : '_';

    // create new radio for advanced list
    const radio_div = createEnvironmentDiv(key, info.description, info.path, info.modules);

    // add radio div to corresponding group in advanced list
    const divgroup_id = group_id + "_group"
    const environmentAdvDivGroup = document.getElementById(divgroup_id);
    if (environmentAdvDivGroup == null) {
      divgroup = document.createElement('div');
      divgroup.id = divgroup_id;
      divgroup.className = "default-environment";
      defaultEnvironmentsDiv.appendChild(divgroup);
      headgroup = document.createElement('h4');
      headgroup.innerText = info.group;
      divgroup.appendChild(headgroup);
      divgroup.appendChild(radio_div);
    } else {
      environmentAdvDivGroup.appendChild(radio_div);
    }

    // create new option for simple menu
    const option = document.createElement('option');
    option.text = info.description;
    option.value = key;

    // add option to corresponding option group in menu
    const optgroup_id = group_id + "_simple";
    const environmentSimpleGroup = document.getElementById(optgroup_id);
    if (environmentSimpleGroup == null) {
      optgroup = document.createElement('optgroup');
      optgroup.id = optgroup_id;
      optgroup.className = "default-environment";
      optgroup.label = info.group;
      environmentSimple.appendChild(optgroup);
      optgroup.appendChild(option);
    } else {
      environmentSimpleGroup.appendChild(option);
    }
  }
  selectEnvironment(selectedKey);
}

function resetSpawnForm() {
  document.getElementById('spawn_form').reset();
  setSimplePartition(window.SLURM_DATA.default_partition);
  restoreCustomEnvironmentsFromLocalStorage();
  updateDefaultUrl();
}

function setVisible(element, visible) {
  if (visible) {
    element.removeAttribute('hidden');
  } else {
    element.setAttribute('hidden', '');
  }
}

function updateEnvironmentAddNameRequired() {
  const environmentAddRadio = document.getElementById('environment_add_radio');
  const environmentAddName = document.getElementById('environment_add_name');
  if (environmentAddRadio.checked) {
    environmentAddName.setAttribute('required', '');
  } else {
    environmentAddName.removeAttribute('required');
  }
}

function setSimplePartition(name) {
  const partitionElem = document.getElementById('partition');
  const gpuDivSimple = document.getElementById('gpu_simple');
  const gpuRadio0Simple = document.getElementById('0Gpu');
  const ngpusElem = document.getElementById('ngpus');
  const fourCoreSimple = document.getElementById('fourCores');
  const quarterCoreSimple = document.getElementById('quarterCore');
  const quarterCoresLabel = document.querySelector(
    `label[for="${quarterCoreSimple.id}"]`
  );
  const nprocsElem = document.getElementById('nprocs');
  const runtimeSelect = document.getElementById('runtime_simple');

  partitionElem.value = name;
  updatePartitionLimits();
  updateDefaultEnvironments();
  createEnvironmentSimpleCustomGroup();

  const info = window.SLURM_DATA.partitions[name];

  // Toggle GPU choice display
  setVisible(gpuDivSimple, info.max_ngpus !== 0);

  // Reset ngpus and GPUs choice
  gpuRadio0Simple.checked = true;
  ngpusElem.value = '0';

  // Update displayed NProcs info and values
  // Get number of CPUs for given paritition choice
  const quarterNProcs = Math.floor(info.max_nprocs / 4);

  quarterCoresLabel.textContent = `${quarterNProcs} cores`;
  quarterCoreSimple.value = quarterNProcs;
  const quarterCoreIsVisible = quarterNProcs > 4;
  setVisible(quarterCoresLabel, quarterCoreIsVisible);
  if (quarterCoreSimple.checked && !quarterCoreIsVisible) {
    fourCoreSimple.checked = true;
    fourCoreSimple.dispatchEvent(new Event('change'));
  }

  // Update nprocs according to current CPUs choice
  const selector = document.querySelector(
    'input[name="nprocs_simple"]:checked'
  );
  nprocsElem.value = selector ? selector.value : '1';

  // Update available runtime options
  // Reset to 1 hour if choice is not available with current partition
  if (runtimeSelect.value * 3600 > info['max_runtime']) {
    runtimeSelect.selectedIndex = 0;
    runtimeSelect.dispatchEvent(new Event('change'));
  }
  for (i = 0; i < runtimeSelect.options.length; i++) {
    const element = runtimeSelect.options[i];
    setVisible(element, element.value * 3600 <= info['max_runtime']);
  }
}

function updateMemValue() {
  const memHiddenElem = document.getElementById('mem');
  const memInputElem = document.getElementById('mem_input');
  const value = memInputElem.value;

  // Pass empty field and 0 as is, append G for others
  memHiddenElem.value = value && value !== '0' ? `${value}G` : value;
}

function updateDefaultUrl() {
  const defaultUrlCheckboxElem = document.getElementById('default_url');
  const defaultUrlHiddenElem = document.getElementById('default_url_hidden_input');

  defaultUrlHiddenElem.value = defaultUrlCheckboxElem.checked ? '/lab' : '/tree';
}

function updatePartitionLimits() {
  const nprocsElem = document.getElementById('nprocs');
  const nprocsSpanElem = document.getElementById('max_nprocs_span');
  const memSpanElem = document.getElementById('max_mem_span');
  const memInputElem = document.getElementById('mem_input');
  const ngpusElem = document.getElementById('ngpus');
  const ngpusSpanElem = document.getElementById('max_ngpus_span');

  const partition = document.getElementById('partition').value;
  const info = window.SLURM_DATA.partitions[partition];

  if (nprocsElem.value > info.max_nprocs) nprocsElem.value = info.max_nprocs;
  nprocsElem.max = info.max_nprocs;
  nprocsSpanElem.textContent = info.max_nprocs;

  const max_mem = Math.floor(info.max_mem / 1024);
  if (memInputElem.value && memInputElem.value > max_mem) {
    memInputElem.value = max_mem;
  }
  memInputElem.max = max_mem;
  memSpanElem.textContent = `${max_mem}GB`;
  updateMemValue();

  if (ngpusElem.value > info.max_ngpus) ngpusElem.value = info.max_ngpus;
  ngpusElem.max = info.max_ngpus;
  ngpusElem.disabled = info.max_ngpus === 0;
  ngpusSpanElem.textContent = info.max_ngpus;

  document.querySelectorAll('input[name="ngpus_simple"]').forEach((element) => {
    const isVisible = element.value <= info.max_ngpus;
    setVisible(element, isVisible);
    setVisible(document.querySelector(`label[for="${element.id}"]`), isVisible);
  });
}

function storeConfigToLocalStorage() {
  const advancedDiv = document.getElementById('menu1');
  const runtimeSelect = document.getElementById('runtime_simple');

  // Retrieve form fields to store
  const fieldNames = [
    'partition',
    'nprocs',
    'mem_input',
    'ngpus',
    'runtime',
    'default_url',
    'output',
    'reservation',
    'options',
  ];
  const fields = {};
  for (const name of fieldNames) {
    const elem = document.getElementById(name);
    if (elem.type && elem.type === 'checkbox') {
      fields[name] = elem.checked;
    } else {
      fields[name] = elem.value;
    }
  }

  // Persist simple inputs
  window.localStorage.setItem(
    CONFIG_NAME,
    JSON.stringify({
      isAdvanced:
        advancedDiv !== null && advancedDiv.classList.contains('active'),
      simple: {
        partitionId: document.querySelector(
          'input[name="partition_simple"]:checked'
        ).id,
        nprocsId: document.querySelector('input[name="nprocs_simple"]:checked')
          .id,
        ngpusId: document.querySelector('input[name="ngpus_simple"]:checked')
          .id,
        runtime: runtimeSelect.value,
      },
      fields: fields,
      environmentId: getSelectedEnvironment(),
    })
  );
}

function restoreConfigFromLocalStorage() {
  const advancedLink = document.getElementById('advanced_tab_link');
  const runtimeSelect = document.getElementById('runtime_simple');

  resetSpawnForm();

  // Load config
  const config = JSON.parse(window.localStorage.getItem(CONFIG_NAME));
  if (config === null) {
    return;
  }

  if (config['isAdvanced']) {
    // Restore advanced tab
    advancedLink.click();

    const fields = config['fields'];
    for (const name in fields) {
      const elem = document.getElementById(name);
      const value = fields[name];
      if (typeof value === 'boolean') {
        elem.checked = value;
      } else {
        elem.value = value;
      }
      elem.dispatchEvent(new Event('change'));
    }
  } else {
    // Restore simple tab
    for (const key of ['partitionId', 'nprocsId', 'ngpusId']) {
      const element = document.getElementById(config['simple'][key]);
      if (element !== null) {
        element.checked = true;
        element.dispatchEvent(new Event('change'));
      }
    }
    runtimeSelect.value = config['simple']['runtime'];
    runtimeSelect.dispatchEvent(new Event('change'));
    // (hardcoded with hidden form element)
    // jupyterlabSimpleElem.checked = config['fields']['default_url'];
    // jupyterlabSimpleElem.dispatchEvent(new Event('change'));
  }

  selectEnvironment(config['environmentId']);
}

// Handle document ready
document.addEventListener('DOMContentLoaded', () => {
  resetSpawnForm(); // Init

  const nprocsElem = document.getElementById('nprocs');
  const ngpusElem = document.getElementById('ngpus');
  const runtimeElem = document.getElementById('runtime');
  const defaultUrlCheckboxElem = document.getElementById('default_url');
  const environmentAddRadio = document.getElementById('environment_add_radio');
  const environmentAddName = document.getElementById('environment_add_name');
  const environmentAddPath = document.getElementById('environment_add_path');
  const environmentAddMods = document.getElementById('environment_add_modules');
  const environmentAddButton = document.getElementById(
    'environment_add_button'
  );

  // Update advanced form from Simple tab inputs
  // Partitions
  document
    .querySelectorAll('input[name="partition_simple"]')
    .forEach((element) => {
      element.addEventListener('change', (e) => {
        setSimplePartition(e.target.value);
      });
    });
  // CPUs
  document
    .querySelectorAll('input[name="nprocs_simple"]')
    .forEach((element) => {
      element.addEventListener('change', (e) => {
        nprocsElem.value = e.target.value;
      });
    });
  // GPUs
  document.querySelectorAll('input[name="ngpus_simple"]').forEach((element) => {
    element.addEventListener('change', (e) => {
      ngpusElem.value = e.target.value;
    });
  });
  // Update default_url hidden input
  defaultUrlCheckboxElem.addEventListener('change', updateDefaultUrl)
  // Runtime
  document.getElementById('runtime_simple').addEventListener('change', (e) => {
    runtimeElem.value = `${e.target.value}:00:00`;
  });

  // Reset when returning to simple tab
  document.getElementById('simple_tab_link').addEventListener('click', () => {
    const config = JSON.parse(window.localStorage.getItem(CONFIG_NAME));
    if (config !== null && !config['isAdvanced']) {
      restoreConfigFromLocalStorage();
    } else {
      resetSpawnForm();
    }
  });

  // Update limits when partition is changed
  document
    .getElementById('partition')
    .addEventListener('change', updatePartitionLimits);

  // Update default jupyter envs when partition is changed
  document
    .getElementById('partition')
    .addEventListener('change', updateDefaultEnvironments);

  // Handle update of environment simple
  document
    .getElementById('environment_simple')
    .addEventListener('change', (e) => selectEnvironment(e.target.value));

  // Handle update of environment advanced
  document
    .getElementById('jupyter_environments_default')
    .addEventListener('change', (e) => selectEnvironment(e.target.value));
  document
    .getElementById('jupyter_environments_custom')
    .addEventListener('change', (e) => selectEnvironment(e.target.value));

  // Update mem when mem_input changes
  document
    .getElementById('mem_input')
    .addEventListener('change', (e) => updateMemValue());

  // Handle add custom environment
  document
    .getElementById('environment_add_name')
    .addEventListener('input', (e) => {
      const isInputEmpty = e.target.value === '';
      if (environmentAddRadio.value === '' && !isInputEmpty) {var myEle = document.getElementById("myElement");
        // First input in the name: select its radio button
        environmentAddRadio.checked = true;
      }
      environmentAddRadio.value = e.target.value;
      environmentAddButton.disabled = isInputEmpty;
    });

  environmentAddRadio.addEventListener(
    'change',
    updateEnvironmentAddNameRequired
  );

  environmentAddButton.addEventListener('click', (e) => {
    const key = `custom-${Date.now()}`; // Poor man's UUID
    addCustomEnvironment(
      key,
      environmentAddName.value,
      environmentAddPath.value,
      environmentAddMods.value
    );
    if (environmentAddRadio.checked) {
      selectEnvironment(key);
      updateEnvironmentAddNameRequired();
    }
    environmentAddName.value = '';
    environmentAddPath.value = '';
    environmentAddMods.value = '';
    environmentAddName.dispatchEvent(new Event('input'));
  });

  // Catch form submit
  document.getElementById('spawn_form').addEventListener('submit', (e) => {
    if (environmentAddRadio.checked) {
      environmentAddButton.dispatchEvent(new Event('click'));
    }
    storeConfigToLocalStorage();
  });

  restoreConfigFromLocalStorage();
});
