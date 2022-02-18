# Spawn Balsam jobs for production
# All stages (gen, g4, detsim, ...) are run in a single job

from time import time
import argparse
from balsam.api import Job, Site, _APIApp

cosmics = False
n_submissions = 32*1     # Number of submissions (== number of prodsingles)
num_nodes = 1            # Number of compute nodes required (> 1 implies MPI usage)
node_packing_count = 32  # Maximum number of concurrent runs per node.
extra_tag = f'{num_nodes}_node_merge_test_{node_packing_count}npc'
fhicl_dir = "/lus/grand/projects/neutrino_osc_ADSP/software/theta_balsam_scripts/fcls/cosmic_tagger/"
if cosmics:
    fhicl_base = "prod_cosmictagger_sample_{sample}.fcl"
else:
    fhicl_base = "prod_cosmictagger_nocosmics_{sample}.fcl"


detector = "sbnd"
software = "sbndcode"
version = "v09_42_00"
qual = "e20:prof"
# prod_fcl = "run_mpvmpr_sbnd.fcl"

# Figure out the site:
site = Site.objects.filter(path="/lus/grand/projects/neutrino_osc_ADSP/cosmic-tagger-feb-22")[0]

timestamp = int(time())
ct_app = _APIApp.objects.filter(site_id=site.id, name="CosmicTagger")[0]
merge_app = _APIApp.objects.filter(site_id=site.id, name="Merge")[0]
preprocess_app = _APIApp.objects.filter(site_id=site.id, name="Preprocess")[0]


# Here, we do the following for train/val/test
# Each larsoft job generates 5 events with cosmic overlay.
#   - It converts that to larcv as well
# There is a larsoft job for all 3 flavors
# Then, a merge job puts the 3 files together into one larcv file.
# Then, a preprocess job does the larcv preprocessing ops
# Then, another merge job puts 15 event files together.
# In total, we target statistics of:
# - 500,000 events in train
# - 50,000 events in val
# - 100,000 events in test
# - 100,000 events in beam-only

# For train/val/test:
# - Generate 5 events per file, 3 samples (WORKGROUP), 10x each, merged into 150 events. (SUBSAMPLE)
# - Preprocess each file, merge 25 preprocessed files into a merged file (3750 events) (PREPROC)
# - Requires 134 workflows in train (5e5 events) (WORKFLOW)
# - Requires 13 workflows in val (5e4 events)
# - Requires 26 workflows in test

# For beam events:
# - generate 5 events at a time, merge 20 together (100 events)
# - 25 jobs together get preprocessed and merged (2500 events)
# - Requires 40 workflows for beam

# Organization:
# - inside the data directory, store things in train/test/val/beam at top level.
# - then, index by workflow (0 to 133 for train, for example)
# - inside there, index by preprocessed file (25)
# - inside there, index by flavor (nueCC, NC, numuCC)
# - inside there, index by subsample (0 to 9)
# - Example workdir is data/train/27/2/nueCC/9


# Computational requirements:
# - First jobs of 5 events take ~30 minutes per core
# - Memory limits to 48 jobs per node.
# - Subsequent jobs *may* run faster.
# - 500000 events * 0.5 hours / 48 jobs per node = 5208 node hours
# - Would require approximately 128 nodes for 40 hours.
# - better estimate needed.

def spawn_larsoft_workgroup(workflow : str, name : str, subsample_index : int, preproc_index : int, events_per_file = 5):
    '''
    Create a group of 3 files (nueCC, numuCC, NC) and return the jobs.
    '''
    sample_jobs = []
    larcv_files = []

    # Spawn a nueCC, numuCC, NC job each time:
    for sample in ["NC", "nueCC", "numuCC"]:
        out_name = f"cosmic_tagger_{sample}_{subsample_index}.root"
        job = Job(
            workdir    = f"{name}/{sample}/{subsample_index}",
            app_id     = ct_app.id,
            tags       = {
                "workflow"  : workflow,
                "sample"    : sample,
                "n_events"  : events_per_file,
                "subsample" : subsample_index,
                "preproc"   : preproc_index},
            parameters = {
                "software"  : software,
                "version"   : version,
                "qual"      : qual,
                "fhicl_dir" : fhicl_dir,
                "fhicl"     : fhicl_base.format(sample=sample),
                "nevts"     : f"{events_per_file}",
                "output"    : out_name,
                },
            node_packing_count = node_packing_count,
            num_nodes = num_nodes,
            parent_ids = (),
        )
        sample_jobs.append(job)
        larcv_files.append(out_name.replace(".root","_larcv.h5"))

    return sample_jobs, larcv_files

def spawn_larsoft_subsample(workflow : str, name : str, n_workgroups : int, preproc_index : int):

    all_jobs         = []
    all_output_files = []
    events_per_file  = 8

    for i in range(n_workgroups):

        jobs, larcv_files = spawn_larsoft_workgroup(
            workflow        = workflow,
            name            = name,
            subsample_index = i,
            preproc_index   = preproc_index,
            events_per_file = events_per_file)


        all_jobs += jobs
        all_output_files += larcv_files

    total_events = events_per_file * 3 * n_workgroups


    # save all the jobs:
    all_jobs = Job.objects.bulk_create(all_jobs)

    # get the parent IDs:
    parent_ids = [s.id for s in all_jobs]


    # create a merge job for these sub samples:
    merge_job = Job(
        workdir = f"{name}/merged/",
        app_id =merge_app.id,
        tags        = {
            "workflow"      : workflow,
            "sample"        : "merge",
            "n_events"      : total_events,
            "preproc"       : preproc_index,
        },
        parameters  = {
            "output_file"   : f"cosmic_tagger_merged_{preproc_index}.h5",
            "input_file_list" : all_output_files,
        },
        node_packing_count = node_packing_count,
        parent_ids=parent_ids
    )
    merge_job.save()


    # And, create a preprocessing job:
    preproc_job = Job(
        workdir = f"{name}/preprocessed/",
        app_id  = preprocess_app.id,
        tags    = {
            "workflow"      : workflow,
            "sample"        : "preproc",
            "n_events"      : total_events,
            "preproc"       : preproc_index,
        },
        parameters = {
            "config" : "/lus/grand/projects/neutrino_osc_ADSP/software/theta_balsam_scripts/apps/preprocess.json",
            "input"  : f"cosmic_tagger_merged_{preproc_index}.h5",
            "output" : f"cosmic_tagger_merged_{preproc_index}_processed.h5"
        },
        node_packing_count = node_packing_count,
        parent_ids = [merge_job.id]
    )
    preproc_job.save()

    # Need to return the job to merge the next steps together
    return preproc_job

def spawn_workflow(name : str, n_workgroups : int, n_sub_workflows, workflow_index : int):

    # We spawn subsamples, collect the preprocess jobs, and merge the outputs together.
    preproc_jobs = []
    for i in range(n_sub_workflows):
        top_dir = f"{name}/{workflow_index}/{i}/"

        job = spawn_larsoft_subsample(name, top_dir, n_workgroups=n_workgroups, preproc_index=i)

        preproc_jobs.append(job)


    parent_ids = [s.id for s in preproc_jobs]

    total_events = 0
    for j in preproc_jobs: total_events += int(j.tags["n_events"])

    output_files = []
    for j in preproc_jobs: output_files.append(j.get_parameters()["output"])

    # create a merge job for these sub samples:
    merge_job = Job(
        workdir = f"{name}/merged_{workflow_index}/",
        app_id  = merge_app.id,
        tags        = {
            "workflow"      : name,
            "sample"        : "merge",
            "n_events"      : total_events,
        },
        parameters  = {
            "output_file"   : f"cosmic_tagger_merged_{workflow_index}.h5",
            "input_file_list" : output_files,
        },
        node_packing_count = node_packing_count,
        parent_ids=parent_ids
    )
    merge_job.save()

    pass

# Testing configuration: just a few small pieces:
# #
name="dev"
if cosmics: name += "_cosmics"
for i_workflow in range(2):
    print(f"{name} workflow {i_workflow}")
    spawn_workflow(name, n_workgroups=5, n_sub_workflows=5, workflow_index=i_workflow)

# name="val"
# for i_workflow in range(13):
#     print(f"{name} workflow {i_workflow}")
#     spawn_workflow(name, n_workgroups=10, n_sub_workflows=25, workflow_index=i_workflow)

# name="test"
# for i_workflow in range(26):
#     print(f"{name} workflow {i_workflow}")
#     spawn_workflow(name, n_workgroups=10, n_sub_workflows=25, workflow_index=i_workflow)


# name="train"
# for i_workflow in range(134):
#     print(f"{name} workflow {i_workflow}")
#     spawn_workflow(name, n_workgroups=10, n_sub_workflows=25, workflow_index=i_workflow)

# spawn_workflow("train_demo", n_workgroups=3, n_sub_workflows=4, workflow_index=1)
