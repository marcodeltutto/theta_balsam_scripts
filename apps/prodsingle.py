from balsam.site import ApplicationDefinition

class ProdSingle(ApplicationDefinition):
    """
    Application description
    """
    environment_variables = {}
    command_template = '''
singularity run -B /lus/grand/projects/neutrino_osc_ADSP:/lus/grand/projects/neutrino_osc_ADSP:rw /lus/grand/projects/neutrino_osc_ADSP/fnal-wn-sl7.sing <<EOF
	#setup SBNDCODE:
	source /lus/grand/projects/neutrino_osc_ADSP/sbndcode/setup
	setup sbndcode v09_24_02 -q e20:prof
	lar -c prodsingle_mu_bnblike.fcl
        ls
EOF
echo "\nJob finished in: $(pwd)"
echo "Available files:"
ls
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
