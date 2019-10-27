# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['main.py'],
             pathex=['F:\\Mucking_Desktop\\src'],
             binaries=[],
             datas=[('F:\\Mucking_Desktop\\src\\ui\\*.ui', 'ui'),
                    ('F:\\Mucking_Desktop\\src\\data\\mucking_2019.*', 'data')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['PyInstaller'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='IIMG Score Tracker',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=True,
          icon="F:\\Mucking_Desktop\\src\\images\\IIMG_Logo.ico")

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='IIMG Score Tracker')
