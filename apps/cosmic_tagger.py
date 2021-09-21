from pathlib import Path
# from balsam.site import ApplicationDefinition
from balsam.api import site_config, ApplicationDefinition

import os
from typing import Dict
import jinja2
import h5py

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

singularity run -B /lus/grand/projects/:/lus/grand/projects/:rw /lus/grand/projects/neutrino_osc_ADSP/containers/fnal-wn-sl7.sing <<EOF

    echo "Running in: "
    pwd
    echo ""
    #setup SBNDCODE:
    source /lus/grand/projects/neutrino_osc_ADSP/software/larsoft/products/setup
    setup {{software}} {{version}} -q {{qual}}
    # get the fcls
    cp -r {{fhicl_dir}}/*.fcl .

    lar -c {{fhicl}} --nevts {{nevts}} --output {{output}}

    # Set up gallery framework
    setup hdf5 v1_10_5a -q e20
    setup cmake v3_18_2
    source /lus/grand/projects/datascience/cadams/gallery-framework/config/setup.sh

    python /lus/grand/projects/datascience/cadams/gallery-framework/UserDev/SuperaLight/supera_sbnd.py --file {{output}}

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
        # Check the output file exists:
        output_file = self.job.get_parameters()['output']
        if not os.path.exists(output_file):
           self.job.state = "FAILED"
           self.job.state_data = {"reason" : f"Output file {output_file} does not exist"}
        output_file = output_file.replace(".root","_larcv.h5")
        if not h5py.is_hdf5(output_file):
           self.job.state = "FAILED"
           print("HDF5 file does not exist!")
           self.job.state_data = {"reason": f"H5Py.is_file returned false for output_file: {output_file}"}
           return

        # Lastly, check that the files have the right number of events.
        with h5py.File(output_file) as h:
            if len(h["Events/event_id"]) == 0:
                print("Length of HDF5 file is 0, ERROR")
                self.job.state_data = {"reason" : "hdf5 file is length 0"}
                self.job.state = "FAILED"


        self.job.state = "POSTPROCESSED"

    def shell_preamble(self):
        pass

    def handle_timeout(self):
        self.job.state = "RESTART_READY"

    def handle_error(self):
        self.job.state = "FAILED"

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
    merge_larcv3_files.py -ol {{output_file}} -il {{input_file_list}}
    '''
    parameters = {}
    transfers = {}

    def preprocess(self):
        # print('Running PREPROCESS for Merge')
        # Get the parent
        # txt_file = open('infiles.txt', 'w')
        for parent in self.job.parent_query():
            # Get the parent's workdir
            parent_workdir = site_config.data_path.joinpath(parent.workdir)  # This is a Path object
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

Merge.sync()

class Preprocess(ApplicationDefinition):
    """
    Application that merges files
    """
    site = "cosmic-tagger-regen"
    environment_variables = {}
    command_template = '''
    source /lus/grand/projects/datascience/cadams/cosmic_tagger_gen_env/bin/activate
    run_processor.py -c {{config}} -il {{input}} -ol {{output}}
    '''
    parameters = {}
    transfers = {}

    def preprocess(self):
        # print('Running PREPROCESS for Preprocess')
        # Get the parent

        for parent in self.job.parent_query():
            # Get the parent's workdir
            parent_workdir = site_config.data_path.joinpath(parent.workdir)  # This is a Path object
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
