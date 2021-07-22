from pathlib import Path
from balsam.site import ApplicationDefinition
from balsam.api import site_config

class ProdAll(ApplicationDefinition):
    """
    An application to run gen, g4, detsim, reco in one go
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
    # export the path the fcl files
    export FHICL_FILE_PATH=$FHICL_FILE_PATH:{{fhicl_dir}}
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




