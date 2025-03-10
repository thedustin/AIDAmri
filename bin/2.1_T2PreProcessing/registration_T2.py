"""
Created on 10/08/2017

@author: Niklas Pallast
Neuroimaging & Neuroengineering
Department of Neurology
University Hospital Cologne

"""


import sys,os
import numpy as np
import nibabel as nii
import glob

def BET_2_MPIreg(inputVolume, stroke_mask,brain_template, allenBrain_template,allenBrain_anno,allenBrain_annorsfMRI,outfile,opt):
    output = os.path.join(outfile, os.path.basename(inputVolume).split('.')[0] + '_TemplateAff.nii.gz')
    outputCPPAff = os.path.join(outfile, os.path.basename(inputVolume).split('.')[0] + 'MatrixAff.txt')
    os.system(
         'reg_aladin -ref ' +inputVolume  + ' -flo ' + brain_template + ' -res ' + output+ ' -aff ' +outputCPPAff)# + ' -fmask ' +MPITemplateMask+ ' -rmask ' + find_mask(inputVolume))


    # Inverse registration
    outputInc = os.path.join(outfile, os.path.basename(inputVolume).split('.')[0] + '_IncidenceData.nii.gz')
    outputIncAff = os.path.join(outfile, os.path.basename(inputVolume).split('.')[0] + 'MatrixInv.txt')
    os.system(
         'reg_aladin  -ref ' + allenBrain_template + ' -flo ' +inputVolume  + ' -res ' + outputInc + ' -aff ' +outputIncAff)

    # if region such as stroke_mask is defined
    if len(stroke_mask) > 0:
        outputIncStrokeMask = os.path.join(outfile, os.path.basename(outputInc).split('.')[0] + '_mask.nii.gz')
        os.system(
            'reg_resample -ref ' + allenBrain_template + ' -flo ' +stroke_mask + ' -trans ' + outputIncAff + ' -res ' + outputIncStrokeMask)

    jac = 0.3
    # minimum defomraiton field in mm
    if opt == 1:
        s = [1, 1, 2]
    elif opt == 2:  s = [2,2,2]
    elif opt == 3:  s = [3,3,3]
    else:           s = [5,5,5]


    outputCPP = os.path.join(outfile, os.path.basename(inputVolume).split('.')[0] + 'MatrixBspline.nii')

    # resample in-house developed template
    output = os.path.join(outfile, os.path.basename(inputVolume).split('.')[0] + '_Template.nii.gz')
    os.system('reg_f3d -ref ' + inputVolume + ' -flo ' + brain_template +
              ' -sx  ' + str(s[0]) + '  -sy ' + str(s[1]) + ' -sz ' + str(s[2]) +
              ' -jl ' + str(jac) +
              ' -res ' + output + ' -cpp ' + outputCPP + ' -aff ' + outputCPPAff)

    # resmaple Allen Brain Reference Template
    outputAnno = os.path.join(outfile, os.path.basename(inputVolume).split('.')[0] + '_TemplateAllen.nii.gz')
    os.system(
        'reg_resample -ref ' + inputVolume + ' -flo ' + allenBrain_template +
        ' -cpp ' + outputCPP + ' -res ' + outputAnno)

    # resample parental annotations
    outputAnnorsfMRI = os.path.join(outfile, os.path.basename(inputVolume).split('.')[0] + '_AnnorsfMRI.nii.gz')
    os.system('reg_resample -ref ' + inputVolume + ' -flo ' + allenBrain_annorsfMRI + ' -inter 0'
                                                                                      ' -cpp ' + outputCPP + ' -res ' + outputAnnorsfMRI)
    # resample annotations
    outputAnno = os.path.join(outfile, os.path.basename(inputVolume).split('.')[0] + '_Anno.nii.gz')
    os.system('reg_resample -ref ' + inputVolume + ' -flo ' + allenBrain_anno + ' -inter 0'
                  
                                                                                ' -cpp ' + outputCPP + ' -res ' + outputAnno)
    return outputAnno

def find_nearest(array,value):
    idx = (np.abs(array-value)).argmin()
    return array[idx]

def clearAnno(araAnno,realBrain_anno,outfile):
    print('NN to reconstruct original Annotations...')
    araData = nii.load(araAnno)
    araVol = araData.get_data()
    nullValues = araVol < 0.0
    araVol[nullValues] = 0.0
    araVol = np.memmap.round(araVol)

    realData = nii.load(realBrain_anno)
    realVal = realData.get_data()
    realVal = realVal.tolist()
    uniqueList = np.unique(realVal)

    for i in np.nditer(araVol,op_flags=['readwrite']):
        i[...] = find_nearest(uniqueList, i)

    scaledNiiData = nii.Nifti1Image(araVol, araData.affine)
    hdrIn = scaledNiiData.header
    hdrIn.set_xyzt_units('mm')
    output_file = os.path.join(outfile, 'reconstructedAnno.nii.gz')
    nii.save(scaledNiiData, output_file)

    return outfile

def find_mask(inputVolume):
    return glob.glob(os.path.dirname(inputVolume)+'/*Stroke_mask.nii.gz', recursive=False)



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Registration from ABA to T2 Data')

    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument('-i', '--inputVolume', help='Path to input file', required=True)

    parser.add_argument('-s', '--deformationStrength', help='integer: 1 - very strong deformation, 2 - strong deformation, 3 - medium deformation, 4 - weak deformation ', nargs='?', type=int,
                        default=3)
    parser.add_argument('-g', '--template', help='File: Templates for Allen Brain', nargs='?', type=str,
                        default=os.path.abspath(os.path.join(os.getcwd(), os.pardir,os.pardir))+'/lib/NP_template_sc0.nii.gz')
    parser.add_argument('-t','--allenBrain_template', help='File: Templates of Allen Brain', nargs='?', type=str,
                        default=os.path.abspath(
                            os.path.join(os.getcwd(), os.pardir, os.pardir)) + '/lib/average_template_50.nii.gz')
    parser.add_argument('-a','--allenBrain_anno', help='File: Annotations of Allen Brain', nargs='?', type=str,
                        default=os.path.abspath(
                            os.path.join(os.getcwd(), os.pardir, os.pardir)) + '/lib/annotation_50CHANGEDanno.nii.gz')
    parser.add_argument('-f', '--allenBrain_annorsfMRI', help='File: Annotations of Allen Brain', nargs='?',
                        type=str,
                        default=os.path.abspath(
                            os.path.join(os.getcwd(), os.pardir, os.pardir)) + '/lib/annoVolume+2000_rsfMRI.nii.gz')

    args = parser.parse_args()

    inputVolume = None
    allenBrain_template = None
    allenBrain_anno = None
    brain_template = None
    allenBrain_annorsfMRI = None
    deformationStrength = args.deformationStrength

    if args.inputVolume is not None:
        inputVolume = args.inputVolume
    if not os.path.exists(inputVolume):
        sys.exit("Error: '%s' is not an existing directory." % (inputVolume,))

    if args.allenBrain_template is not None:
        allenBrain_template = args.allenBrain_template
    if not os.path.exists(allenBrain_template):
        sys.exit("Error: '%s' is not an existing directory." % (allenBrain_template,))

    if args.allenBrain_anno is not None:
        allenBrain_anno = args.allenBrain_anno
    if not os.path.exists(allenBrain_anno):
        sys.exit("Error: '%s' is not an existing directory." % (allenBrain_anno,))

    if args.allenBrain_annorsfMRI is not None:
        allenBrain_annorsfMRI = args.allenBrain_annorsfMRI
    if not os.path.exists(allenBrain_annorsfMRI):
        sys.exit("Error: '%s' is not an existing directory." % (allenBrain_annorsfMRI,))

    if args.template is not None:
        brain_template = args.template
    if not os.path.exists(brain_template):
        sys.exit("Error: '%s' is not an existing directory." % (brain_template,))


    outfile = os.path.join(os.path.dirname(inputVolume))
    if not os.path.exists(outfile):
        os.makedirs(outfile)

    stroke_mask = find_mask(inputVolume)
    if len(stroke_mask) is 0:
        stroke_mask = []
        print("Notice: '%s' has no defined reference (stroke) mask - will proceed without." % (inputVolume,))
    else:
        stroke_mask = stroke_mask[0]

    print("T2 Registration \33[5m...\33[0m (wait!)", end="\r")
    # generate log - file
    sys.stdout = open(os.path.join(os.path.dirname(inputVolume), 'reg.log'), 'w')

    transInput = BET_2_MPIreg(inputVolume, stroke_mask,brain_template,allenBrain_template,allenBrain_anno,allenBrain_annorsfMRI,outfile,deformationStrength)
    #result = ARA_2_input(transInput, allenBrain_template, allenBrain_anno ,outfile)
    sys.stdout = sys.__stdout__
    print('T2 Registration  \033[0;30;42m COMPLETED \33[0m')


