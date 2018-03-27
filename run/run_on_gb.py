__author__ = 'mcychen'

import sys, os, errno, time
# add the parent directory to the paths
sys.path.insert(1, os.path.join(sys.path[0], '..'))

import multi_v_fit as mvf
import aic
import clean_map


#=======================================================================================================================
'''
This is a wrapper to run on the Green Bank server for the multi_vlsr package
'''
#=======================================================================================================================

class Region(object):
    '''
    A Class that contains all the relevant file path and run the pipeline fitting and analysis
    '''

    # base_all_rebase3 is no good root for the moment being (e.g., netagive baseline)
    def __init__(self, region_name, root='all_rebase3', rootPara = None):

        self.region = region_name
        self.rootDir = "/lustre/pipeline/scratch/GAS"
        self.cubeDir = "{0}/images".format(self.rootDir)
        self.paraDir = "{0}/{1}/paraMaps_MChen".format(self.cubeDir, self.region)
        self.modelDir = "{0}/{1}/multi_v_models_MChen".format(self.cubeDir, self.region)
        self.cleanParaDir = "{0}/clean_maps".format(self.paraDir)

        # create directories if they don't exist
        make_dir(self.paraDir)
        make_dir(self.modelDir)
        make_dir(self.cleanParaDir)

        self.root = root
        if rootPara is None:
            self.rootPara = self.root

        # defining paths to imaged data
        self.OneOneFile = '{2}/{0}/{0}_NH3_11_{1}.fits'.format(self.region, self.root, self.cubeDir)
        self.RMSFile = '{2}/{0}/{0}_NH3_11_{1}_rms.fits'.format(self.region, self.root, self.cubeDir)
        self.SingVParaFile = '{2}/{0}/{0}_parameter_maps_{1}.fits'.format(self.region, self.rootPara, self.cubeDir)


    def start_timing(self, message = True):
        # timestamp the start a timing interval
        if message:
            print "...start timing..."
        self.start_time = time.time()


    def end_timing(self):
        # timestamp the end of a timing interval and print the time elapsed
        end = time.time()
        delta_time = int(end - self.start_time)
        print "time elapsed: {0}:{1}".format(delta_time/60, delta_time%60)


    def fit_cube(self, n_comp, multicore=8, snr_min=5.0, mask_function = None):

        self.start_timing()

        # defining paths to the imaged data
        # NOTE: given that there are multiple components, the following attributes are better implamented as
        # dictoinaries than just a single string
        self.NewParaFile = '{2}/{0}_{3}vcomp_parameter_maps_{1}.fits'.format(self.region, self.rootPara, self.paraDir,
                                                                             n_comp)
        self.ModelFile = '{2}/{0}_NH3_11_{1}_{3}comp_model.fits'.format(self.region, self.root, self.modelDir,
                                                                        n_comp)
        self.ChisqFile = '{2}/{0}_{3}vcomp_chisq_{1}.fits'.format(self.region, self.rootPara, self.paraDir, n_comp)

        self.SNRFile = '{2}/{0}_{3}vcomp_SNR_eachV_{1}.fits'.format(self.region, self.rootPara, self.paraDir, n_comp)
        self.SepVModelFile = '{2}/{0}_NH3_11_{1}_{3}VModel.fits'.format(self.region, self.root, self.modelDir, n_comp)

        if os.path.exists(self.SingVParaFile):
            guesses = mvf.make_guesses(self.SingVParaFile, n_comp = n_comp)
        else:
            guesses = None

        # fit the data
        self.paraCubes = mvf.cubefit_gen(cube11name = self.OneOneFile, ncomp = n_comp , paraname = self.NewParaFile,
                                 modname = self.ModelFile, chisqname = self.ChisqFile, guesses = guesses,
                                 errmap11name = self.RMSFile, multicore = multicore,
                                 snr_min=snr_min, mask_function = mask_function)

        mvf.get_multiV_models(paraname=self.NewParaFile, refcubename=self.OneOneFile, n_comp = n_comp,
                              savename = self.SepVModelFile, snrname = self.SNRFile, rms = 0.15, rmspath=self.RMSFile)
        self.end_timing()


    def calc_aic(self, n_comp1=1, n_comp2=2):
        # calculate the aic values over the same spectral windows for two given models
        modpath1 = '{2}/{0}_NH3_11_{1}_{3}comp_model.fits'.format(self.region, self.root, self.modelDir, n_comp1)
        modpath2 = '{2}/{0}_NH3_11_{1}_{3}comp_model.fits'.format(self.region, self.root, self.modelDir, n_comp2)
        aiccpath = "{0}/{1}_NH3_11_{2}v{3}comp_aicc.fits".format(self.cleanParaDir, self.region, n_comp2, n_comp1)
        aic.fits_comp_AICc(self.OneOneFile, modpath1, modpath2, aiccpath)


    def calc_chisq(self, n_comp1=1, n_comp2=2):
        # calculate the reduced chi-squared values over the same spectral windows two given models
        modpath1 = '{2}/{0}_NH3_11_{1}_{3}comp_model.fits'.format(self.region, self.root, self.modelDir, n_comp1)
        modpath2 = '{2}/{0}_NH3_11_{1}_{3}comp_model.fits'.format(self.region, self.root, self.modelDir, n_comp2)
        chisqpath = "{0}/{1}_NH3_11_{2}v{3}comp_redchisq.fits".format(self.cleanParaDir, self.region, n_comp2, n_comp1)
        aic.fits_comp_chisq(self.OneOneFile, modpath1, modpath2, chisqpath, reduced = True)


    def clean_paramap(self):
        return None



#=======================================================================================================================
# here are some quick utilities functions

def make_dir(dirpath):
    # create directories if they don't exist
    try:
        os.makedirs(dirpath)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise



#=======================================================================================================================



def super_run():
    special_run(region='L1448')
    special_run(region='OrionB_NGC2023-2024')
    '''
    run(region='OrionA')
    run(region='IC5146')
    run(region='OrionB_NGC2068-2071')
    run(region='Serpens_Aquila')
    run(region='L1688')
    '''

def special_run(region='L1448', multicore=8):
    # for rebase that does not have other first look properties
    regOb = Region(region, root='base_all_rebase3')
    # use Jared's multi-rebased file
    regOb.OneOneFile = '{2}/{0}/{0}_NH3_11_{1}.fits'.format(regOb.region, 'all_rebase_multi', regOb.cubeDir)

    #regOb.fit_cube(n_comp=1, multicore=multicore, snr_min=5.0, mask_function = None)
    regOb.fit_cube(n_comp=2, multicore=multicore, snr_min=5.0, mask_function = None)
    regOb.calc_aic()
    regOb.calc_chisq()


def run(region='L1448', multicore=8, root='all_rebase3'):
    # wrapper to run individual regions on a go

    regOb = Region(region, root=root)
    regOb.fit_cube(n_comp=1, multicore=multicore, snr_min=5.0, mask_function = None)
    regOb.fit_cube(n_comp=2, multicore=multicore, snr_min=5.0, mask_function = None)
    regOb.calc_aic()
    regOb.calc_chisq()


'''
# currenlty I plan to do the cleaning locally on mcychen
def clean():
    clean_map.clean(oriname, newname, snrname = snrname, one_v_map = one_v_name, aic_maps = aicname,
          fill_plane1 = False, mergesim = False, rm_sml_obj = True, sort_method = "None")
'''