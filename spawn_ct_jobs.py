# Spawn Balsam jobs for production
# All stages (gen, g4, detsim, ...) are run in a single job

from time import time
import argparse
from balsam.api import Job, App, Site


n_submissions = 64*2     # Number of submissions (== number of prodsingles)
n_events = 20            # Number of events per submission
num_nodes = 1            # Number of compute nodes required (> 1 implies MPI usage)
node_packing_count = 64  # Maximum number of concurrent runs per node.
extra_tag = '1_node_sbnd_test'
fhicl_dir = "/grand/projects/datascience/cadams/theta_balsam_scripts/fcls/cosmic_tagger/"
fhicl_base = "prod_cosmictagger_sample_{sample}.fcl"


detector = "sbnd"
software = "sbndcode"
version = "v09_27_00_02"
qual = "e20:prof"
# prod_fcl = "run_mpvmpr_sbnd.fcl"

# FIgure out the site:
site = Site.objects.filter(path="/grand/projects/datascience/cadams/cosmic-tagger-regen")[0]
print(site)

timestamp = int(time())
ct_app = App.objects.get(site_id=site.id, class_path="cosmic_tagger.CosmicTagger")
print(ct_app)

for j in range(n_submissions):
    if j % 10 == 0: print('Spawning submission:', j)

    sample_jobs = []


    # Spawn a nueCC, numuCC, NC job each time:
    for sample in ["NC", "nueCC", "numuCC"]:
        job = Job(
            workdir=f"prod_cosmictagger/{sample}/{j}/",
            app_id=ct_app.id,
            tags={"sample":sample, 'n_submissions': n_submissions, 'n_events': n_events, 'extra': extra_tag},
            parameters={
                "software": software,
                "version": version,
                "qual": qual,
                "fhicl_dir": fhicl_dir,
                "fhicl": fhicl_base.format(sample=sample),
                "nevts": f"{n_events}",
                "output": f"cosmic_tagger_{sample}.root"},
            node_packing_count=node_packing_count,
            num_nodes=num_nodes,
            parent_ids=(),
        )
        job.save()
        sample_jobs.append(job)

    # Here would be a merge job for the larcv output:


    # for i in range(n_events):

    # print(job)
