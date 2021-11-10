from pathlib import Path
# from balsam.site import ApplicationDefinition
from balsam.api import site_config, ApplicationDefinition

import os
from typing import Dict
import jinja2
import h5py
import subprocess

# echo $'#{{fcl_name}}\nphysics.bs.s: "3"' > wrapped_{{{{fcl_name}}}}
# lar -c prodsingle_mu_bnblike.fcl --nevts {{nevts}} --output {{output}}
# lar -c /lus/grand/projects/neutrino_osc_ADSP/software/larsoft/fcls/prodsingle_muon_sbnd.fcl --nevts {{nevts}} --output {{output}}
class CosmicTagger(ApplicationDefinition):
    """
    Generate files for CosmicTagger
    """
    site = "cosmic-tagger-regen"
    environment_variables = {}
    command_template = '''
echo "Job starting!"
date
hostname
echo "Current directory: "
pwd
set -e

singularity run -B /lus/grand/projects/:/lus/grand/projects/:rw /lus/grand/projects/neutrino_osc_ADSP/containers/fnal-wn-sl7.sing <<EOF

    echo "Running in: "
    pwd
    echo ""
    #setup SBNDCODE:
    source /lus/grand/projects/neutrino_osc_ADSP/software/larsoft/products/setup
    setup {{software}} {{version}} -q {{qual}}
    # get the fcls
    cp -r {{fhicl_dir}}/*.fcl .

    set -e
    lar -c {{fhicl}} --nevts {{nevts}} --output {{output}}
    set +e

EOF
echo "Job finishing!"
date
echo "\nJob finished in: $(pwd)"
echo "Available files:"
ls
hostname
'''
    parameters = {}
    transfers = {}
    cleanup_files = ["*.root", "*.db", "*core", ".fcl"]

    def preprocess(self):
        self.job.state = "PREPROCESSED"

    def postprocess(self):
        # several cleanup actions:


        # This check happens in handle error too:
        # Check the output file exists:
        output_file = self.job.get_parameters()['output']
        if not os.path.exists(output_file):
           self.job.state = "FAILED"
           self.job.state_data = {"reason" : f"Output file {output_file} does not exist"}
           return

        parameters = self.job.get_parameters()
        # Postproc command:
            # Set up gallery framework

        postproc = '''
singularity run -B /lus/grand/projects/:/lus/grand/projects/:rw /lus/grand/projects/neutrino_osc_ADSP/containers/fnal-wn-sl7.sing <<EOF
    source /lus/grand/projects/neutrino_osc_ADSP/software/larsoft/products/setup
    setup {software} {version} -q {qual}

    setup hdf5 v1_10_5a -q e20
    setup cmake v3_18_2
    source /lus/grand/projects/datascience/cadams/gallery-framework/config/setup.sh

    set -e
    python /lus/grand/projects/datascience/cadams/gallery-framework/UserDev/SuperaLight/supera_sbnd.py --file {output}
    set +e
EOF
'''.format(
    software = parameters['software'],
    version  = parameters['version'],
    qual     = parameters['qual'],
    output   = parameters['output'],
    )

        subprocess.run(postproc, shell=True)

        larcv_file = output_file.replace(".root","_larcv.h5")
        if not h5py.is_hdf5(larcv_file):
           self.job.state = "RUN_DONE"
           self.job.state_data = {"reason": f"H5Py.is_file returned false for larcv_file: {larcv_file}"}
           return

        # Lastly, check that the files have the right number of events.
        with h5py.File(larcv_file) as h:
            if len(h["Events/event_id"]) == 0:
                print("Length of HDF5 file is 0, ERROR")
                self.job.state_data = {"reason" : "hdf5 file is length 0"}
                self.job.state = "FAILED"
                return

        os.unlink(output_file)  # CWD already set for this job
        self.job.state = "POSTPROCESSED"

    def shell_preamble(self):
        pass

    def handle_timeout(self):
        self.job.state = "RESTART_READY"

    def handle_error(self):

        print("Handling Error")
        # If the output file exists, we declare a successful Job
        # regardless of exit code
        output_file = self.job.get_parameters()['output']
        print("Output File is ", output_file)
        print("Handling error for this job, return code is ", self.job.return_code)
        if os.path.exists(output_file):
            self.job.state = "RUN_DONE"
            print("Marking as run done despite aborted job, since output file exists.")
            return
        elif self.job.return_code == 139:
            self.job.state = "RESTART_READY"
            return
        else:
            self.job.state = "FAILED"
            return

CosmicTagger.sync()


# --source-list infiles.txt
class Merge(ApplicationDefinition):
    """
    Application that merges files
    """
    site = "cosmic-tagger-regen"
    environment_variables = {}
    command_template = '''
    source /lus/grand/projects/datascience/cadams/cosmic_tagger_gen_env/bin/activate
    merge_larcv3_files.py -ol {{output_file}} -il {% for inp in input_file_list %} {{inp}} {% endfor %}
    '''
    # command_template = '''
    # source /lus/grand/projects/datascience/cadams/cosmic_tagger_gen_env/bin/activate
    # merge_larcv3_files.py -ol {{output_file}} -il {{input_file_list}}
    # '''
    parameters = {}
    transfers = {}

    def preprocess(self):
        # print('Running PREPROCESS for Merge')
        # Get the parent
        # txt_file = open('infiles.txt', 'w')

        data_path = Path.cwd()
        while data_path.name != "data":
           data_path = data_path.parent

        for parent in self.job.parent_query():
            # Get the parent's workdir
            parent_workdir = data_path.joinpath(parent.workdir)  # This is a Path object
            parent_files = parent_workdir.glob("c*.h5")
            for i, parent_root_file in enumerate(parent_files):
                if not Path(parent_root_file).is_symlink():
                    # Only symlink newly created files (not files that were previously symlinked)
                    Path(parent_root_file.name).symlink_to(parent_root_file)
                    # txt_file.write(parent_root_file.name + '\n')
        # txt_file.close()
        # print('End Running PREPROCESS for Merge')

        self.job.state = "PREPROCESSED"

    def _render_shell_command(self) -> str:
            """
            Args:
                - arg_dict: value for each required parameter
            Returns:
                - str: shell command with safely-escaped parameters
                Use shlex.split() to split the result into args list.
                Do *NOT* use string.join on the split list: unsafe!
            """
            arg_dict = {**self._default_params, **self.job.get_parameters()}
            diff = set(self.parameters.keys()).difference(arg_dict.keys())
            if diff:
                raise ValueError(f"Missing required args: {diff} (only got: {arg_dict})")

            #sanitized_args = {key: shlex.quote(str(arg_dict[key])) for key in self.parameters}
            return jinja2.Template(self.command_template).render(arg_dict)

    def postprocess(self):
        self.job.state = "POSTPROCESSED"

    def shell_preamble(self):
        pass

    def handle_timeout(self):
        self.job.state = "RESTART_READY"

    def handle_error(self):
        self.job.state = "FAILED"

Merge.sync()


class Preprocess(ApplicationDefinition):
    """
    Application that merges files
    """
    site = "cosmic-tagger-regen"
    environment_variables = {}
    command_template = '''
    source /lus/grand/projects/datascience/cadams/cosmic_tagger_gen_env/bin/activate
    run_processor.py -c {{config}} -il {% for inp in input_file_list %} {{inp}} {% endfor %} -ol {{output}}
    '''
    parameters = {}
    transfers = {}

    def preprocess(self):
        # print('Running PREPROCESS for Preprocess')
        # Get the parent

        data_path = Path.cwd()
        while data_path.name != "data":
           data_path = data_path.parent

        for parent in self.job.parent_query():
            # Get the parent's workdir
            parent_workdir = data_path.joinpath(parent.workdir)  # This is a Path object
            parent_files = parent_workdir.glob("c*.h5")
            for i, parent_root_file in enumerate(parent_files):
                if not Path(parent_root_file).is_symlink():
                    # Only symlink newly created files (not files that were previously symlinked)
                    Path(parent_root_file.name).symlink_to(parent_root_file)
                    # txt_file.write(parent_root_file.name + '\n')
        # txt_file.close()
        # print('End Running PREPROCESS for Merge')

        self.job.state = "PREPROCESSED"

    def _render_command(self, arg_dict: Dict[str, str]) -> str:
        diff = set(self.parameters.keys()).difference(arg_dict.keys())
        if diff:
            raise ValueError(f"Missing required args: {diff} (only got: {arg_dict})")

        # sanitized_args = {key: shlex.quote(str(arg_dict[key])) for key in self.parameters}
        return jinja2.Template(self.command_template).render(arg_dict)

    def postprocess(self):
        self.job.state = "POSTPROCESSED"

    def shell_preamble(self):
        pass

    def handle_timeout(self):
        self.job.state = "RESTART_READY"

    def handle_error(self):
        self.job.state = "FAILED"

Preprocess.sync()
