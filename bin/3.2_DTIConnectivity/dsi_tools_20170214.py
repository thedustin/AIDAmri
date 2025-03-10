"""
Created on 10/08/2017

@author: Niklas Pallast
Neuroimaging & Neuroengineering
Department of Neurology
University Hospital Cologne

Documentation preface, added 23/05/09 by Victor Vera Frazao:
This document is currently in revision for improvement and fixing.
Specifically changes are made to allow compatibility of the pipeline with Ubuntu 18.04 systems 
and Ubuntu 18.04 Docker base images, respectively, as well as adapting to appearent changes of 
DSI-Studio that were applied since the AIDAmri v.1.1 release. As to date the DSI-Studio version 
used is the 2022/08/03 Ubuntu 18.04 release.
All changes and additional documentations within this script carry a signature with the writer's 
initials (e.g. VVF for Victor Vera Frazao) and the date at application, denoted after '//' at 
the end of the comment line. If code segments need clearance the comment line will be prefaced 
by '#?'. Changes are prefaced by '#>' and other comments are prefaced ordinalrily 
by '#'.
"""


from __future__ import print_function

import os
import re
import sys
import time
import glob
import nibabel as nii
import numpy as np
import nipype.interfaces.fsl as fsl

import shutil
import subprocess


def scaleBy10(input_path, inv):
    data = nii.load(input_path)
    imgTemp = data.get_data()
    if inv is False:
        scale = np.eye(4) * 10
        scale[3][3] = 1
        scaledNiiData = nii.Nifti1Image(imgTemp, data.affine * scale)
        fslPath = os.path.join(os.path.dirname(input_path), 'fslScaleTemp.nii.gz')
        nii.save(scaledNiiData, fslPath)
        return fslPath
    elif inv is True:
        scale = np.eye(4) / 10
        scale[3][3] = 1
        unscaledNiiData = nii.Nifti1Image(imgTemp, data.affine * scale)
        hdrOut = unscaledNiiData.header
        hdrOut.set_xyzt_units('mm')

        # hdrOut['sform_code'] = 1
        nii.save(unscaledNiiData, input_path)
        return input_path
    else:
        sys.exit("Error: inv - parameter should be a boolean.")


def findSlicesData(path, pre):
    regMR_list = []
    fileALL = glob.iglob(path + '/' + pre + '*.nii.gz', recursive=True)
    for filename in fileALL:
        regMR_list.append(filename)
    regMR_list.sort()
    return regMR_list


def fsl_SeparateSliceMoCo(input_file, par_folder):
    # scale Nifti data by factor 10
    dataName = os.path.basename(input_file).split('.')[0]
    fslPath = scaleBy10(input_file, inv=False)
    mySplit = fsl.Split(in_file=fslPath, dimension='z', out_base_name=dataName)
    print(mySplit.cmdline)
    mySplit.run()
    os.remove(fslPath)

    # sparate ref and src volume in slices
    sliceFiles = findSlicesData(os.getcwd(), dataName)
    print('For all slices ... ')

    # start to correct motions slice by slice
    for i in range(len(sliceFiles)):
        slc = sliceFiles[i]
        output_file = os.path.join(par_folder, os.path.basename(slc))
        myMCFLIRT = fsl.preprocess.MCFLIRT(in_file=slc, out_file=output_file, save_plots=True, terminal_output='none')
        print(myMCFLIRT.cmdline)
        myMCFLIRT.run()
        os.remove(slc)

    # merge slices to a single volume
    mcf_sliceFiles = findSlicesData(par_folder, dataName)
    output_file = os.path.join(os.path.dirname(input_file),
                               os.path.basename(input_file).split('.')[0]) + '_mcf.nii.gz'
    myMerge = fsl.Merge(in_files=mcf_sliceFiles, dimension='z', merged_file=output_file)
    print(myMerge.cmdline)
    myMerge.run()

    for slc in mcf_sliceFiles: 
        os.remove(slc)

    # unscale result data by factor 10**(-1)
    output_file = scaleBy10(output_file, inv=True)

    return output_file


def make_dir(dir_out, dir_sub):
    """
    Creates new directory.
    """
    dir_out = os.path.normpath(os.path.join(dir_out, dir_sub))
    if not os.path.exists(dir_out):
        print("Create directory \"%s\"" % (dir_out,))
        os.mkdir(dir_out)
        time.sleep(1.0)
        if not os.path.exists(dir_out):
            sys.exit("Could not create directory \"%s\"" % (dir_out,))
    return dir_out

def move_files(dir_in, dir_out, pattern):
    time.sleep(1.0)
    file_list = glob.glob(dir_in+pattern)
    file_list.sort()

    time.sleep(1.0)
    for file_mv in file_list: # move files from input to output directory
        file_in = os.path.join(dir_in, file_mv)
        print("Move file \"%s\" to directory \"%s\"" % (file_in, dir_out))
        shutil.copy(file_in, dir_out)

    for file_mv in file_list: # remove files in output directory
        file_out = os.path.join(dir_out, file_mv)
        if os.path.isfile(file_out):
            os.remove(file_out)

def connectivity(dsi_studio, dir_in, dir_seeds, dir_out, dir_con):
    """
    Calculates connectivity data (types: pass and end).
    """
    if not os.path.exists(dir_in):
        sys.exit("Input directory \"%s\" does not exist." % (dir_in,))

    dir_seeds = os.path.normpath(os.path.join(dir_in, dir_seeds))
    if not os.path.exists(dir_seeds):
        sys.exit("Seeds directory \"%s\" does not exist." % (dir_seeds,))

    if not os.path.exists(dir_out):
        sys.exit("Output directory \"%s\" does not exist." % (dir_out,))

    dir_con = make_dir(dir_out, dir_con)

    # change to input directory
    os.chdir(os.path.dirname(dir_in))
    cmd_ana = r'%s --action=%s --source=%s --tract=%s --connectivity=%s --connectivity_value=%s --connectivity_type=%s'

    filename = glob.glob(dir_in+'/*fib.gz')[0]
    file_trk = glob.glob(dir_in+'/*trk.gz')[0]
    file_seeds = dir_seeds

    # Performs analysis on every connectivity value within the list ('qa' may not be necessary; might be removed in the future.)
    connect_vals = ['qa', 'count']
    for i in connect_vals:
        parameters = (dsi_studio, 'ana', filename, file_trk, file_seeds, i, 'pass,end')
        os.system(cmd_ana % parameters)

    #move_files(dir_in, dir_con, re.escape(filename) + '\.' + re.escape(pre_seeds) + '.*(?:\.pass\.|\.end\.)')
    move_files(os.path.dirname(file_trk), dir_con, '/*.txt')
    move_files(os.path.dirname(file_trk), dir_con, '/*.mat')

def mapsgen(dsi_studio, dir_in, dir_msk, b_table, pattern_in, pattern_fib):
    """
    FUNCTION DEPRECATED. REMOVAL PENDING.
    """
    pre_msk = 'bet.bin.'

    ext_src = '.src.gz'
    ext_nii = '.nii.gz'

    if not os.path.exists(dir_in):
        sys.exit("Input directory \"%s\" does not exist." % (dir_in,))

    dir_msk = os.path.normpath(os.path.join(dir_in, dir_msk))
    if not os.path.exists(dir_msk):
        sys.exit("Masks directory \"%s\" does not exist." % (dir_msk,))

    b_table = os.path.join(dir_in, b_table)
    if not os.path.isfile(b_table):
        sys.exit("File \"%s\" does not exist." % (b_table,))

    # change to input directory
    os.chdir(dir_in)

    cmd_src = r'%s --action=%s --source=%s --output=%s --b_table=%s'
    cmd_rec = r'%s --action=%s --source=%s --mask=%s --method=%d --param0=%s --thread_count=%d --check_btable=%d'

    file_list = [x for x in os.listdir(dir_in) if os.path.isfile(os.path.join(dir_in, x)) and re.match(pattern_in, x)]
    file_list.sort()

    for index, filename in enumerate(file_list):
        # create source files
        pos = filename.rfind('_')

        file_src = filename[:pos] + ext_src
        parameters = (dsi_studio, 'src', filename, file_src, b_table)
        print("%d of %d:" % (index + 1, len(file_list)), cmd_src % parameters)
        subprocess.call(cmd_src % parameters)

        # create fib files
        file_msk = os.path.join(dir_msk, pre_msk + filename[:pos] + ext_nii)
        parameters = (dsi_studio, 'rec', file_src, file_msk, 3, '16', 2, 0)
        print("%d of %d:" % (index + 1, len(file_list)), cmd_rec % parameters)
        subprocess.call(cmd_rec % parameters)

    # extracts maps: 2 ways:
    cmd_exp = r'%s --action=%s --source=%s --export=%s'

    file_list = [x for x in os.listdir(dir_in) if os.path.isfile(os.path.join(dir_in, x)) and re.match(pattern_fib, x)]
    file_list.sort()

    for index, filename in enumerate(file_list):
        #file_fib = os.path.join(dir_in, filename)
        #parameters = (dsi_studio, 'exp', file_fib, 'fa')
        parameters = (dsi_studio, 'exp', filename, 'fa')
        print("%d of %d:" % (index + 1, len(file_list)), cmd_exp % parameters)
        subprocess.call(cmd_exp % parameters)

def srcgen(dsi_studio, dir_in, dir_msk, dir_out, b_table):
    """
    Sources and creates fib files. Diffusivity and aniosotropy metrics are exported from data.
    """
    dir_src = r'src'
    dir_fib = r'fib_map'
    dir_qa  = r'DSI_studio'
    dir_con = r'connectivity'
    ext_src = '.src.gz'

    if not os.path.exists(dir_in):
        sys.exit("Input directory \"%s\" does not exist." % (dir_in,))

    dir_msk = os.path.normpath(os.path.join(dir_in, dir_msk))
    if not os.path.exists(dir_msk):
        sys.exit("Masks directory \"%s\" does not exist." % (dir_msk,))

    if not os.path.exists(dir_out):
        sys.exit("Output directory \"%s\" does not exist." % (dir_out,))

    b_table = os.path.join(dir_in, b_table)
    if not os.path.isfile(b_table):
        sys.exit("File \"%s\" does not exist." % (b_table,))

    dir_src = make_dir(os.path.dirname(dir_out), dir_src)
    dir_fib = make_dir(os.path.dirname(dir_out), dir_fib)
    dir_qa  = make_dir(os.path.dirname(dir_out), dir_qa)

    # change to input directory
    os.chdir(os.path.dirname(dir_in))

    cmd_src = r'%s --action=%s --source=%s --output=%s --b_table=%s'
    cmd_rec = r'%s --action=%s --source=%s --mask=%s --method=%d --param0=%s --check_btable=%d --half_sphere=%d'

    # create source files
    filename = os.path.basename(dir_in)
    pos = filename.rfind('.')
    file_src = os.path.join(dir_src, filename[:pos] + ext_src)
    parameters = (dsi_studio, 'src', filename, file_src, b_table)
    print("Generate src-File %s:" % cmd_src % parameters)
    os.system(cmd_src % parameters)

    # create fib files
    file_msk = dir_msk
    parameters = (dsi_studio, 'rec', file_src, file_msk, 1, '16', 0, 1)
    print("Generate fib-File %s:" % cmd_rec % parameters)
    os.system(cmd_rec % parameters)

    # move fib to corresponding folders
    move_files(dir_src, dir_fib, '/*fib.gz')

    # extracts maps: 2 ways:
    cmd_exp = r'%s --action=%s --source=%s --export=%s'
    file_fib = glob.glob(dir_fib+'/*fib.gz')[0]
    parameters = (dsi_studio, 'exp', file_fib, 'fa')
    print("Generate two maps %s:" % cmd_exp % parameters)
    os.system(cmd_exp % parameters)

    # extracts maps: 2 ways:
    cmd_exp = r'%s --action=%s --source=%s --export=%s'
    file_fib = glob.glob(dir_fib + '/*fib.gz')[0]
    parameters = (dsi_studio, 'exp', file_fib, 'md')
    print("Generate two maps %s:" % cmd_exp % parameters)
    os.system(cmd_exp % parameters)

    # extracts maps: 2 ways:
    cmd_exp = r'%s --action=%s --source=%s --export=%s'
    file_fib = glob.glob(dir_fib + '/*fib.gz')[0]
    parameters = (dsi_studio, 'exp', file_fib, 'ad')
    print("Generate two maps %s:" % cmd_exp % parameters)
    os.system(cmd_exp % parameters)

    # extracts maps: 2 ways:
    cmd_exp = r'%s --action=%s --source=%s --export=%s'
    file_fib = glob.glob(dir_fib + '/*fib.gz')[0]
    parameters = (dsi_studio, 'exp', file_fib, 'rd')
    print("Generate two maps %s:" % cmd_exp % parameters)
    os.system(cmd_exp % parameters)

    move_files(dir_fib, dir_qa, '/*qa.nii.gz')
    move_files(dir_fib, dir_qa, '/*fa.nii.gz')
    move_files(dir_fib, dir_qa, '/*md.nii.gz')
    move_files(dir_fib, dir_qa, '/*ad.nii.gz')
    move_files(dir_fib, dir_qa, '/*rd.nii.gz')

def tracking(dsi_studio, dir_in):
    """
    Performs seed-based fiber-tracking.
    """
    if not os.path.exists(dir_in):
        sys.exit("Input directory \"%s\" does not exist." % (dir_in,))

    # change to input directory
    os.chdir(os.path.dirname(dir_in))

    # qa threshold for 60/65 = 0.05; for Alzheimer: 0.03
    cmd_trk = r'%s --action=%s --source=%s --output=%s --fiber_count=%d --interpolation=%d --step_size=%s --turning_angle=%s --check_ending=%d --fa_threshold=%s --smoothing=%s --min_length=%s --max_length=%s'

    filename = glob.glob(dir_in+'/*fib.gz')[0]
    parameters = (dsi_studio, 'trk', filename, os.path.join(dir_in, filename+'.trk.gz'), 1000000, 0, '.5', '55', 0, '.02', '.1', '.5', '12.0')
    print("Track neuronal pathes %s:" % cmd_trk % parameters)
    os.system(cmd_trk % parameters)

if __name__ == '__main__':
    pass
