from balsam.api import Job, App, site_config
from time import time

n_submissions = 2       # Number of submissions (== number of prodsingles)
n_events = 5            # Number of events per submission
num_nodes = 1            # Number of compute nodes required (> 1 implies MPI usage)
node_packing_count = 64  # Maximum number of concurrent runs per node.
extra_tag = '1_node_sbnd_test'
fhicl_dir = "/lus/grand/projects/neutrino_osc_ADSP/production/theta_balsam_scripts/fcls/"

detector = "sbnd"
software = "sbndcode"
version = "v09_26_00"
qual = "e20:prof"
prod_fcl = "run_mpvmpr_sbnd.fcl"

# detector = "icarus"
# software = "icaruscode"
# version = "v09_26_00"
# qual = "e20:prof"
# prod_fcl = "run_mpvmpr_icarus.fcl"

timestamp = int(time())

for j in range(n_submissions):
    print('Spawning submission:', j)
    #
    # ProdMultiPart
    #
    prodsingle_app = App.objects.get(site_id=site_config.site_id, class_path="production_all.ProdAll")
    prodsingle_jobs = []

    # for i in range(n_events):
    job = Job(
        workdir=f"prod_mpvmpr_all/{timestamp}/{j}/",
        app_id=prodsingle_app.id,
        tags={detector:'prod_mpvmpr_all', 'n_submissions': n_submissions, 'n_events': n_events, 'extra': extra_tag},
        parameters={
            "software": software,
            "version": version,
            "qual": qual,
            "fhicl_dir": fhicl_dir,
            "fhicl": prod_fcl,
            "nevts": f"{n_events}",
            "output": f"prod_mpvmpr_{detector}.root"},
        node_packing_count=node_packing_count,
        num_nodes=num_nodes,
        parent_ids=(),
    )
    # print(job)
    job.save()
    prodsingle_jobs.append(job)











