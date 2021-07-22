from balsam.api import Job, App, site_config
from time import time

n_submissions = 2       # Number of submissions (== number of prodsingles)
n_events = 5            # Number of events per submission
num_nodes = 1            # Number of compute nodes required (> 1 implies MPI usage)
node_packing_count = 64  # Maximum number of concurrent runs per node.
extra_tag = '1_node_icarus_test'
fhicl_dir = "/lus/grand/projects/neutrino_osc_ADSP/software/larsoft/fcls/"

# detector = "sbnd"
# software = "sbndcode"
# version = "v09_26_00"
# qual = "e20:prof"
# prod_fcl = fhicl_dir + "run_larsoft_sim_mpvmpr_3d_sbnd.fcl"
# g4_fhicl = "standard_g4_sbnd.fcl"
# detsim_fhicl = "standard_detsim_sbnd.fcl"

detector = "icarus"
software = "icaruscode"
version = "v09_26_00"
qual = "e20:prof"
prod_fcl = fhicl_dir + "run_larsoft_sim_mpvmpr_3d_icarus.fcl"
g4_fhicl = "g4_enable_spacecharge.fcl"
detsim_fhicl = "multitpc_detsim_icarus.fcl"

timestamp = int(time())

for j in range(n_submissions):
    print('Spawning submission:', j)
    #
    # ProdMultiPart
    #
    prodsingle_app = App.objects.get(site_id=site_config.site_id, class_path="production.ProdMultiPart")
    prodsingle_jobs = []

    for i in range(1):
        job = Job(
            workdir=f"prod_prodmultipart/{timestamp}/{j}/{i}",
            app_id=prodsingle_app.id,
            tags={detector:'prodmultipart', 'n_submissions': n_submissions, 'n_events': n_events, 'extra': extra_tag},
            parameters={
                "software": software,
                "version": version,
                "qual": qual,
                "fhicl": prod_fcl,
                "nevts": f"{n_events}",
                "output": f"prod_{detector}_{i}_%#.root"}, # '%#' is replace with the event number
            node_packing_count=node_packing_count,
            num_nodes=num_nodes,
            parent_ids=(),
        )
        # print(job)
        job.save()
        prodsingle_jobs.append(job)


    #
    # Geant4
    #
    geant4_app = App.objects.get(site_id=site_config.site_id, class_path="production.Geant4")
    geant4_jobs = []

    for i in range(n_events):
        job = Job(
            workdir=f"prod_geant4/{timestamp}/{j}/{i}",
            app_id=geant4_app.id,
            tags={detector:'geant4', 'n_submissions': n_submissions, 'n_events': n_events, 'extra': extra_tag},
            parameters={
                "software": software,
                "version": version,
                "qual": qual,
                "fhicl": g4_fhicl,
                "nevts": "1",
                "nskip": "0", # f"{i}",
                "output": f"prod_geant4_{detector}_{i}.root",
                "source": f"prod_{detector}_0_{i+1}.root"}, # f"{prodsingle_jobs[0].parameters['output']}"},
            node_packing_count=node_packing_count,
            num_nodes=num_nodes,
            parent_ids={prodsingle_jobs[0].id},
        )
        # print(job)
        job.save()
        geant4_jobs.append(job)


    #
    # DetSim
    #
    detsim_app = App.objects.get(site_id=site_config.site_id, class_path="production.DetSim")
    detsim_jobs = []

    for i in range(n_events):
        job = Job(
            workdir=f"prod_detsim/{timestamp}/{j}/{i}",
            app_id=detsim_app.id,
            tags={detector:'detsim', 'n_submissions': n_submissions, 'n_events': n_events, 'extra': extra_tag},
            parameters={
                "software": software,
                "version": version,
                "qual": qual,
                "fhicl": detsim_fhicl,
                "nevts": "1",
                "nskip": "0",
                "output": f"prod_geant4_detsim_{detector}_{i}.root",
                "source": f"{geant4_jobs[i].parameters['output']}"},
            node_packing_count=node_packing_count,
            num_nodes=num_nodes,
            parent_ids={geant4_jobs[i].id},
        )
        # print(job)
        job.save()
        detsim_jobs.append(job)



    #
    # Merge
    #
    merge_app = App.objects.get(site_id=site_config.site_id, class_path="production.Merge")
    merge_jobs = []

    for i in range(1):
        job = Job(
            workdir=f"prod_merge/{timestamp}/{j}/{i}",
            app_id=merge_app.id,
            tags={detector:'merge', 'n_submissions': n_submissions, 'n_events': n_events, 'extra': extra_tag},
            parameters={
                "software": software,
                "version": version,
                "qual": qual,
                "nevts": f"{n_events}",
                "nskip": "0",
                "output": f"prod_geant4_detsim_merge_{detector}_{j}.root"},
            node_packing_count=node_packing_count,
            num_nodes=num_nodes,
            parent_ids={detsim_job.id for detsim_job in detsim_jobs},
        )
        # print(job)
        job.save()
        merge_jobs.append(job)










