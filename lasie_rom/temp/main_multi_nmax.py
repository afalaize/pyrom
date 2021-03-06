# -*- coding: utf-8 -*-
"""
Created on Tue Feb 28 17:08:50 2017

@author: afalaize
"""

import os

from pypod.readwrite.vtu2hdf import pvd2Hdf, format_data_name, dumpArrays2Hdf

from pypod.readwrite.read_hdf import (HDFData, HDFTimeSerie,
                                      interpTimeSerieToHdf)
from pypod.config import PVDNAME

from pypod.grids.tools import buildGrid, grid2mesh

from pypod.pod.tools import compute_kinetic_energy
from pypod.pod.pod import (ts2HdfDataMatrix, dataMatrix2MeanAndFluc,
                           fluc2CorrMatrix, computePODBasis,
                           mean2MeanGradient, basis2BasisGradient,
                           checkPODBasisIsOrthonormal,
                           computeModesEnergy)

from pypod.readwrite.write_vtu import write_vtu

from pypod.rom.rom import (build_rom_coefficients_A,
                           build_rom_coefficients_B,
                           build_rom_coefficients_C,
                           build_rom_coefficients_F,
                           ReducedOrderModel)

import numpy as np

import progressbar

import matplotlib.pyplot as plt

actions = {'ALL': False,
           'vtu2hdf': False,
           'interpolate': False,
           'ts2data': False,
           'data2meanAndFluc': False,
           'fluc2Corr': False,
           'corr2basis': True,
           'gradients': True,
           'writeVtu': False,
           'Thost_temporal_coeffs': True,
           'rom': True
           }
nmodes = range(5, 50, 5)
errors = list()
for nmax in nmodes:
    ###############################################################################
    
    # OSX USB: /Volumes/AFALAIZE/cylindre2D_SCC_windows/Results
    # WIn: F:\TESTS_THOST\cylindre2D_SCC_windows\Results
    
    CONFIG = {'vtu_folder': r'F:\TESTS_THOST\cylindre2D_SCC_windows\Results',
              'data_names_vtu': [r'Vitesse(m/s)',
                                 r'MasseVolumique(kg/m3)',
                                 r'Eta'],
              'h': (0.005, )*3,
              'threshold': 0,
              'nmax': nmax,
              'stab': 0.2,
              'dt': 0.01,
              'tend': 52.5,
              'theta': .5,
              'load': {'imin': 20, 'imax': 270, 'decim': 1},
              }
    
    ###############################################################################
    
    CONFIG['hdf_folder'] = CONFIG['vtu_folder'] + os.sep + 'hdf5'
    CONFIG['interp_hdf_folder'] = CONFIG['vtu_folder'] + os.sep + \
        'hdf5_interpolated'
    CONFIG['hdf_path_dataMatrix'] = CONFIG['interp_hdf_folder'] + os.sep + \
        'data.hdf5'
    CONFIG['hdf_path_grid'] = CONFIG['interp_hdf_folder'] + os.sep + 'grid.hdf5'
    CONFIG['hdf_path_mean'] = CONFIG['interp_hdf_folder'] + os.sep + 'mean.hdf5'
    CONFIG['hdf_path_meanGradient'] = CONFIG['interp_hdf_folder'] + os.sep + \
        'meanGradient.hdf5'
    CONFIG['hdf_path_meanDeformation'] = CONFIG['interp_hdf_folder'] + os.sep + \
        'meanDeformation.hdf5'
    CONFIG['hdf_path_weightingMatrix'] = None
    CONFIG['hdf_path_fluc'] = CONFIG['interp_hdf_folder'] + os.sep + 'fluc.hdf5'
    CONFIG['hdf_path_corr'] = CONFIG['interp_hdf_folder'] + os.sep + 'corr.hdf5'
    CONFIG['hdf_path_podBasis'] = CONFIG['interp_hdf_folder'] + os.sep + \
        'basis.hdf5'
    CONFIG['hdf_path_podBasisGradient'] = CONFIG['interp_hdf_folder'] + os.sep + \
        'basisGradient.hdf5'
    CONFIG['hdf_path_A'] = CONFIG['interp_hdf_folder'] + os.sep + 'coeffs_A.hdf5'
    CONFIG['hdf_path_B'] = CONFIG['interp_hdf_folder'] + os.sep + 'coeffs_B.hdf5'
    CONFIG['hdf_path_C'] = CONFIG['interp_hdf_folder'] + os.sep + 'coeffs_C.hdf5'
    CONFIG['hdf_path_F'] = CONFIG['interp_hdf_folder'] + os.sep + 'coeffs_F.hdf5'
    CONFIG['vtu_path_podBasis'] = CONFIG['interp_hdf_folder'] + os.sep + \
        'basis.vtu'
    CONFIG['hdf_path_Thost_temporal_coeffs'] = CONFIG['interp_hdf_folder'] + \
        os.sep + 'Thost_temporal_coeffs.hdf5'
    
    
    ###############################################################################
    
    def plot_kinetic_energy():
        folder = CONFIG['hdf_folder']
        TS = HDFTimeSerie(folder)
        data_name = format_data_name(CONFIG['data_names_vtu'][0])
        path = folder + os.sep + 'data.hdf5'
        load = CONFIG['load']
        ts2HdfDataMatrix(TS, data_name, path, **load)
        data = HDFData(path, openFile=True)
        e = compute_kinetic_energy(data.get_single_data())
        plt.plot(TS.times, e, 'o:')
        plt.title('Energie cinetique')
        data.closeHdfFile()
    
    
    def convert_vtu2hdf():
        pvd_path = CONFIG['vtu_folder'] + os.sep + PVDNAME
        pvd2Hdf(pvd_path, CONFIG['hdf_folder'], CONFIG['data_names_vtu'],
                **CONFIG['load'])
        plot_kinetic_energy()
    
    
    ###############################################################################
    
    def interpolate_data_over_regular_grid():
        TS = HDFTimeSerie(CONFIG['hdf_folder'])
        TS.openAllFiles()
    
        # A regular (1+N)-dimensional grid. E.g with N=3, grid[c, i, j, k] is the
        # component ‘c’ of the coordinates of the point at position (i, j, k).
        grid, grid_h = buildGrid(TS.data[0].getMeshMinMax(), CONFIG['h'])
        grid_shape = grid.shape
        grid_mesh = grid2mesh(grid)
        dumpArrays2Hdf([grid_mesh, np.array(grid_shape)[:, np.newaxis],
                        np.array(grid_h)[:, np.newaxis]],
                       ['mesh', 'original_shape', 'h'], CONFIG['hdf_path_grid'])
        interpTimeSerieToHdf(TS, grid_mesh, CONFIG['interp_hdf_folder'])
        TS.closeAllFiles()
    
    
    ###############################################################################
    
    def form_data_matrix():
        print('Form data matrix')
        TS = HDFTimeSerie(CONFIG['interp_hdf_folder'])
        ts2HdfDataMatrix(TS, format_data_name(CONFIG['data_names_vtu'][0]),
                         CONFIG['hdf_path_dataMatrix'], **CONFIG['load'])
        data = HDFData(CONFIG['hdf_path_dataMatrix'], openFile=True)
        e = compute_kinetic_energy(data.get_single_data())
        plt.plot(e, 'o:')
        plt.title('Energie cinetique')
    
    
    ###############################################################################
    
    def split_mean_and_fluc():
        print('Split mean from fluctuating velocity')
        dataMatrix2MeanAndFluc(CONFIG['hdf_path_dataMatrix'],
                               CONFIG['hdf_path_mean'], CONFIG['hdf_path_fluc'])
    
    
    ###############################################################################
    
    def form_correlation_matrix():
        print('Form correlation matrix')
        fluc2CorrMatrix(CONFIG['hdf_path_fluc'], CONFIG['hdf_path_corr'],
                        hdf_path_weightingMatrix=None)
        C = HDFData(CONFIG['hdf_path_corr'], openFile=True)
        
        plt.figure()
        plt.semilogy(1+np.array(range(len(C.eigen_vals[:]))), C.eigen_vals[:], 'o')
        plt.xlabel(r'indice $i$')
        plt.ylabel(r'valeur propre $\alpha_i$')
        plt.title("Amplitudes des valeurs propres")
        plt.savefig('valeurs_propres.png', format='png')
    
        computeModesEnergy(C.eigen_vals[:, 0])
        plt.figure()
        N = 50
        vals = 100*(1-np.array(computeModesEnergy(C.eigen_vals[:N, 0])))
        plt.semilogy(1+np.array(range(len(vals))), vals, 'o')
        plt.xlim([1, N+1])
        plt.ylabel('erreur %')
        plt.xlabel(r'nombre de modes retenus')
        plt.title("Erreur relative a priori sur l'energie cinetique")
        plt.savefig('erreur.png', format='png')
        C.closeHdfFile()
    
    ###############################################################################
    
    def form_pod_basis():
        print('Form pod basis')
        computePODBasis(CONFIG['hdf_path_corr'], CONFIG['hdf_path_fluc'],
                        CONFIG['hdf_path_podBasis'], threshold=CONFIG['threshold'],
                        nmax=CONFIG['nmax'])
        basis = HDFData(CONFIG['hdf_path_podBasis'])
        basis.openHdfFile()
        checkPODBasisIsOrthonormal(basis.get_single_data())
        basis.closeHdfFile()
    
    
    ###############################################################################
    
    def form_gradients():
        print('Form mean gradient')
        mean2MeanGradient(CONFIG['hdf_path_mean'], CONFIG['hdf_path_meanGradient'],
                          CONFIG['hdf_path_grid'])
        print('Form basis gradient')
        basis2BasisGradient(CONFIG['hdf_path_podBasis'],
                            CONFIG['hdf_path_podBasisGradient'],
                            CONFIG['hdf_path_grid'])
    
    
    ###############################################################################
    
    def export_pod_basis_to_vtu():
        print('write vtu for pod basis')
        basis = HDFData(CONFIG['hdf_path_podBasis'], openFile=True)
        grid = HDFData(CONFIG['hdf_path_grid'], openFile=True)
        write_vtu(grid.mesh[:], grid.original_shape,
                  [data[:, :] for data in basis.get_single_data().swapaxes(0, 1)],
                  'PODmode', CONFIG['vtu_path_podBasis'])
        basis.closeHdfFile()
        grid.closeHdfFile()
    
    
    ###############################################################################
    
    
    def compute_Thost_temporal_coeffs():
        HDFbasis = HDFData(CONFIG['hdf_path_podBasis'], openFile=True)
        basis = HDFbasis.get_single_data()
        HDFbasis.closeHdfFile()
    
        fluct = HDFData(CONFIG['hdf_path_fluc'], openFile=True)
    
        def compute_coeff(u):
            return np.einsum('mc,mic->i', u, basis)
    
        nt = fluct.vitesse.shape[1]
        temporal_coeffs = list()
        bar = progressbar.ProgressBar(widgets=['Coefficients temporels: ',
                                               progressbar.Timer(), ' ',
                                               progressbar.Bar(), ' (',
                                               progressbar.ETA(), ')\n', ])
    
        for i in bar(range(nt)):
            temporal_coeffs.append(compute_coeff(fluct.vitesse[:, i, :]))
    
        fluct.closeHdfFile()
        dumpArrays2Hdf([np.array(temporal_coeffs)],
                       ['coeffs'],
                       CONFIG['hdf_path_Thost_temporal_coeffs'])
    #    mean = HDFData(CONFIG['hdf_path_mean'], openFile=True).get_single_data()
    #    
    #    grid = HDFData(CONFIG['hdf_path_grid'], openFile=True)
    #    for i, coeffs in enumerate(temporal_coeffs):
    #        v = mean + np.einsum('i,mic->mc', coeffs, basis)
    #        write_vtu(grid.mesh[:], grid.original_shape,
    #                  [v, ],
    #                  'vitesse', CONFIG['vtu_folder'] + os.sep + 'reconstructed'+ os.sep + 'vitesse_{}.vtu'.format(i+1))
    #    grid.closeHdfFile()
            
            
    def export_snapshots_ROM(rom):
        config = rom.config
        basis = HDFData(config['hdf_path_podBasis'], openFile=True).get_single_data()
        mean = HDFData(config['hdf_path_mean'], openFile=True).get_single_data()
        grid = HDFData(config['hdf_path_grid'], openFile=True)
        folder = 'reconstructed_ROM'
        pvd_file = open(config['vtu_folder'] + os.sep + folder + os.sep + 'vitesse.pvd', 'w')
        pvd_file.write("""<VTKFile type="Collection" version="0.1" byte_order="LittleEndian">
        <Collection>""")
        template = '\n        <DataSet timestep="{0}" group="" part="0" file="{1}"/>'
     
        for i, coeffs in enumerate(rom.c_rom()[:-2]):
            v = mean + np.einsum('i,mic->mc', coeffs, basis)
            vtu_path = config['vtu_folder'] + os.sep + folder+ os.sep + 'vitesse_{}.vtu'.format(i+1)
            write_vtu(grid.mesh[:], grid.original_shape,
                      [v, ],
                      'vitesse', vtu_path)
            pvd_file.write(template.format(rom.times[i], vtu_path))
        pvd_file.write("""
        </Collection>
    </VTKFile>""")
        pvd_file.close()
        grid.closeHdfFile()
        
    def compute_ROM_error(rom):
        config = rom.config
        HDFbasis = HDFData(config['hdf_path_podBasis'], openFile=True)
        basis = HDFbasis.get_single_data()
        HDFbasis.closeHdfFile()
        mean = HDFData(config['hdf_path_mean'], openFile=True).get_single_data()
        grid = HDFData(config['hdf_path_grid'], openFile=True)
        ts = HDFTimeSerie(CONFIG['interp_hdf_folder'])
        errors = list()
        for i, coeffs in enumerate(rom.c_rom()[:-2]):
            v = mean + np.einsum('i,mic->mc', coeffs, basis)
            d = ts.data[i]
            d.openHdfFile()
            error = v-d.vitesse[:]
            norm_error = np.sqrt(np.einsum('mc,mc', error, error))
            norm_v = np.sqrt(np.einsum('mc,mc', d.vitesse[:], d.vitesse[:]))
            errors.append(norm_error/norm_v)
            d.closeHdfFile()
        grid.closeHdfFile()
        return errors
        
        
    def run_rom():
        ts = HDFTimeSerie(CONFIG['interp_hdf_folder'])
        ts.data[0].openHdfFile()
        rho = ts.data[0].massevolumique[:].flatten()[0]
        mu = ts.data[0].eta[:].flatten()[0]
        build_rom_coefficients_A(CONFIG['hdf_path_podBasis'],
                                 CONFIG['hdf_path_A'])
    
        build_rom_coefficients_B(CONFIG['hdf_path_podBasis'],
                                 CONFIG['hdf_path_podBasisGradient'],
                                 CONFIG['hdf_path_mean'],
                                 CONFIG['hdf_path_meanGradient'], mu, rho,
                                 CONFIG['stab'],
                                 CONFIG['hdf_path_B'])
    
        build_rom_coefficients_C(CONFIG['hdf_path_podBasis'],
                                 CONFIG['hdf_path_podBasisGradient'],
                                 CONFIG['hdf_path_C'])
    
        build_rom_coefficients_F(CONFIG['hdf_path_podBasis'],
                                 CONFIG['hdf_path_podBasisGradient'],
                                 CONFIG['hdf_path_mean'],
                                 CONFIG['hdf_path_meanGradient'], mu, rho,
                                 CONFIG['stab'],
                                 CONFIG['hdf_path_F'])
        rom = ReducedOrderModel(CONFIG)
        rom.run(dt=CONFIG['dt'], tend=CONFIG['tend'], theta=CONFIG['theta'])
        for i in range(rom.npod()):
            plt.figure()
            plt.plot(ts.times, rom.c_fom(i), ':o', label='fom')
            plt.plot(rom.times, rom.c_rom(i)[:-1], '-x', label='rom')
            plt.title('mode {}'.format(i+1))
            plt.legend()
            plt.grid('on')
            plt.savefig('nmode={}_mode{}_dt={:.2f}_rho={:.2f}_mu={:.5f}.png'.format(CONFIG['nmax'], i+1, rom.dt, rho, mu), 
                        format='png')
            plt.show()
        rom.close_hdfs()
        return rom
    ###############################################################################
    
    if actions['vtu2hdf'] or actions['ALL']:
        convert_vtu2hdf()
    if actions['interpolate'] or actions['ALL']:
        interpolate_data_over_regular_grid()
    if actions['ts2data'] or actions['ALL']:
        form_data_matrix()
    if actions['data2meanAndFluc'] or actions['ALL']:
        split_mean_and_fluc()
    if actions['fluc2Corr'] or actions['ALL']:
        form_correlation_matrix()
    if actions['corr2basis'] or actions['ALL']:
        form_pod_basis()
    if actions['gradients'] or actions['ALL']:
        form_gradients()
    if actions['writeVtu'] or actions['ALL']:
        export_pod_basis_to_vtu()
    if actions['Thost_temporal_coeffs'] or actions['ALL']:
        compute_Thost_temporal_coeffs()
    if actions['rom'] or actions['ALL']:
        rom = run_rom()
        errors.append(compute_ROM_error(rom))
    
