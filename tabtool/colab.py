"""Integration with Colab notebooks"""
import os
import re
import nbformat
import logging
from tabtool.utils import run_cmd, find_files, split_config_str

def generate_notebooks(config, eval_dir, colab_dir):
    """Add a colab setup code cell and then save to colab_dir"""
    if not config['github_repo']:
        return
    # copy notebook fron eval_dir to colab_dir
    run_cmd(['rm -rf', colab_dir])
    run_cmd(['cp -r', eval_dir, colab_dir])
    notebooks = find_files('**/*.ipynb', colab_dir)
    for fn in notebooks:
        with open(fn, 'r') as f:
            notebook = nbformat.read(f, as_version=4)
        # Use Python3 as the kernel
        notebook['metadata'].update({"kernelspec": {
            "name": "python3",
            "display_name": "Python 3"
        }})
        # Check if GPU is needed
        use_gpu = False
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                if config['gpu_pattern'] in cell.source:
                    use_gpu = True
                    break
        if use_gpu:
            notebook['metadata'].update({"accelerator": "GPU"})
            logging.info('Use GPU for '+fn)
        # Update SVG image URLs
        if config['replace_svg_url']:
            update_svg_urls(notebook, config['replace_svg_url'], fn, colab_dir)
        # Add additional libraries
        if config['libs']:
            cell = get_installation_cell(notebook, config['libs'])
            if cell:
                notebook.cells.insert(0, cell)
                if config['libs_header']:
                    notebook.cells.insert(
                        0, nbformat.v4.new_markdown_cell(source=config['libs_header']))
        with open(fn, 'w') as f:
            f.write(nbformat.writes(notebook))

def update_svg_urls(notebook, pattern, filename, root_dir):
    orgin_url, new_url = split_config_str(pattern, 2)[0]
    svg_re = re.compile('!\[.*\]\(([\.-_\w\d]+\.svg)\)')
    for cell in notebook.cells:
        if cell.cell_type == 'markdown':
            lines = cell.source.split('\n')
            for i, l in enumerate(lines):
                m = svg_re.search(l)
                if not m:
                    continue
                path = os.path.relpath(os.path.realpath(os.path.join(
                    root_dir, os.path.basename(filename), m[1])), root_dir)
                if not path.startswith(orgin_url):
                    logging.warning("%s in %s does not start with %s"
                                    "specified by replace_svg_url"%(
                                        path, filename, orgin_url))
                else:
                    url = new_url + path[len(orgin_url):]
                    lines[i] = l.replace(m[1], url)
            cell.source = '\n'.join(lines)

def get_installation_cell(notebook, libs):
    """Return a cell for installing the additional libs"""
    lib_dict = dict(split_config_str(libs, 2))
    lib1_re = re.compile('from ([_\w\d]+) import')
    lib2_re = re.compile('import ([_\w\d]+)')
    find_libs = []
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            lines = cell.source.split('\n')
            for l in lines:
                if l.strip().startswith('#'): # it's a comment
                    continue
                m = lib1_re.search(l)
                if not m:
                    m = lib2_re.search(l)
                if m and m[1] in lib_dict:
                    find_libs.append(m[1])
    if not find_libs:
        return None
    install_str = ''
    for lib in set(find_libs):
        for l in lib_dict[lib].split(' '):
            install_str += '!pip install ' + l + '\n'
    return nbformat.v4.new_code_cell(source=install_str)


def add_button(config, html_dir):
    """Add an open colab button in HTML"""
    if not config['github_repo']:
        return
    files = find_files('**/*.html', html_dir, config['exclusions'])
    for fn in files:
        with open(fn, 'r') as f:
            html = f.read()
        if 'id="colab"' in html:
            continue
        colab_link = 'https://colab.research.google.com/github/%s/blob/master/%s'%(
            config['github_repo'],
            os.path.relpath(fn, html_dir).replace('.html', '.ipynb'))
        colab_html = '<a href="%s"> <button style="float:right", id="colab" class="mdl-button mdl-js-button mdl-button--primary mdl-js-ripple-effect"> <i class=" fas fa-external-link-alt"></i> Colab </button></a><div class="mdl-tooltip" data-mdl-for="colab"> Open notbook in Colab</div>' % (colab_link)
        html = html.replace('</h1>', colab_html+'</h1>')
        with open(fn, 'w') as f:
            f.write(html)
