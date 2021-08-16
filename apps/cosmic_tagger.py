from pathlib import Path
from balsam.site import ApplicationDefinition
from balsam.api import site_config

# echo $'#{{fcl_name}}\nphysics.bs.s: "3"' > wrapped_{{{{fcl_name}}}}
# lar -c prodsingle_mu_bnblike.fcl --nevts {{nevts}} --output {{output}}
# lar -c /lus/grand/projects/neutrino_osc_ADSP/software/larsoft/fcls/prodsingle_muon_sbnd.fcl --nevts {{nevts}} --output {{output}}
class CosmicTagger(ApplicationDefinition):
    """
    Generate files for CosmicTagger
    """
    environment_variables = {}
    command_template = '''
echo "Job starting!"
date
hostname
singularity run -B /lus/grand/projects/neutrino_osc_ADSP:/lus/grand/projects/neutrino_osc_ADSP:rw /lus/grand/projects/neutrino_osc_ADSP/containers/fnal-wn-sl7.sing <<EOF
    #setup SBNDCODE:
    source /lus/grand/projects/neutrino_osc_ADSP/software/larsoft/products/setup
    # setup sbndcode v09_24_02 -q e20:prof
    setup {{software}} {{version}} -q {{qual}}
    lar -c {{fhicl}} --nevts {{nevts}} --output {{output}}
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

    def preprocess(self):
        self.job.state = "PREPROCESSED"

    def postprocess(self):
        self.job.state = "POSTPROCESSED"

    def shell_preamble(self):
        pass

    def handle_timeout(self):
        self.job.state = "RESTART_READY"

    def handle_error(self):
        self.job.state = "FAILED"



# --source-list infiles.txt
class Merge(ApplicationDefinition):
    """
    Application that merges files
    """
    environment_variables = {}
    command_template = '''
echo "Job starting!"
date
hostname
singularity run -B /lus/grand/projects/neutrino_osc_ADSP:/lus/grand/projects/neutrino_osc_ADSP:rw /lus/grand/projects/neutrino_osc_ADSP/containers/fnal-wn-sl7.sing <<EOF
    #setup SBNDCODE:
    source /lus/grand/projects/neutrino_osc_ADSP/software/larsoft/products/setup
    # setup sbndcode v09_24_02 -q e20:prof
    setup {{software}} {{version}} -q {{qual}}
    touch empty.fcl
    lar -c empty.fcl --nevts {{nevts}} --nskip {{nskip}} --output {{output}} --source p*.root
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

    def preprocess(self):
        # print('Running PREPROCESS for Merge')
        # Get the parent
        # txt_file = open('infiles.txt', 'w')
        for parent in self.job.parent_query():
            # Get the parent's workdir
            parent_workdir = site_config.data_path.joinpath(parent.workdir)  # This is a Path object
            parent_files = parent_workdir.glob("p*.root")
            for i, parent_root_file in enumerate(parent_files):
                if not Path(parent_root_file).is_symlink():
                    # Only symlink newly created files (not files that were previously symlinked)
                    Path(parent_root_file.name).symlink_to(parent_root_file)
                    # txt_file.write(parent_root_file.name + '\n')
        # txt_file.close()
        # print('End Running PREPROCESS for Merge')

        self.job.state = "PREPROCESSED"

    def postprocess(self):
        self.job.state = "POSTPROCESSED"

    def shell_preamble(self):
        pass

    def handle_timeout(self):
        self.job.state = "RESTART_READY"

    def handle_error(self):
        self.job.state = "FAILED"
