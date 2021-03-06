#!/usr/bin/env python
# encoding: utf-8
# Hans-Martin von Gaudecker and Philipp Kloke, 2012-13

"""
Run a Python script in the directory specified by **ctx.bldnode**.

Select a Python version by specifying the **version** keyword for
the task generator instance as integer 2 or 3. Default is 3.

Any string passed to the **add_to_pythonpath** keyword will be appended to the
PYTHONPATH environmetal variable; strings supplied to the **prepend** and
**append** keywords will be added to the command line.

Usage::

	ctx(
		features='run_py_script',
		source='some_script.py',
		target=['some_table.tex', 'some_figure.eps'],
		deps='some_data.csv',
		add_to_pythonpath='src/some/library',
		append='',
		prepend=''
	)

"""

import os
from waflib import Task, TaskGen, Logs


def configure(conf):
	conf.find_program('python', var='RUN_PY_SCRIPT_CMD', mandatory=False)
	if not conf.env.RUN_PY_SCRIPT_CMD:
		conf.fatal("No Python interpreter found!")


@Task.update_outputs
class run_py_script(Task.Task):
	"""Run a Python script."""

	run_str = '${PREPEND} ${RUN_PY_SCRIPT_CMD} ${SRC[0].abspath()} ${APPEND}'
	shell = True

	def exec_command(self, cmd, **kw):
		bld = self.generator.bld
		try:
			if not kw.get('cwd', None):
				kw['cwd'] = bld.cwd
		except AttributeError:
				bld.cwd = kw['cwd'] = bld.variant_dir
		if not self.buffer_output:
			kw["stdout"] = kw["stderr"] = None
		return bld.exec_command(cmd, **kw) 

@TaskGen.feature('run_py_script')
@TaskGen.before_method('process_source')
def apply_run_py_script(tg):
	"""Task generator for running a single Python module.

	The generated task will honor the PYTHONPATH environmental variable
	as well as a PYTHONPATH attribute of the build context environment.

	Attributes:

		* source -- A **single** source node or string. (required)
		* target -- A single target or list of targets (nodes or strings).
		* deps -- A single dependency or list of dependencies
		  (nodes or strings)
		* add_to_pythonpath -- A string that will be appended to the
		  PYTHONPATH environment variable along with the appropriate
		  path separator.
		* prepend -- A string that will be prepended to the command
		* append -- A string that will be appended to the command

	"""

	# Convert sources and targets to nodes
	src_node = tg.path.find_resource(tg.source)
	if not src_node:
		tg.bld.fatal(
			'Cannot find input file %s for processing' % tg.source
		)
	tgt_nodes = [tg.path.find_or_declare(t) for t in tg.to_list(tg.target)]


	# Create the task.
	tsk = tg.create_task('run_py_script', src=src_node, tgt=tgt_nodes)

	tsk.env.APPEND = getattr(tg, 'append', '')
	tsk.env.PREPEND = getattr(tg, 'prepend', '')
	tsk.buffer_output = getattr(tg, 'buffer_output', True)

	# Custom execution environment
	tsk.env.env = dict(os.environ)
	if tsk.env.env.get('PYTHONPATH', None):
		pythonpath = [tsk.env.env['PYTHONPATH']]
	else:
		pythonpath = []
	if getattr(tsk.env, 'PYTHONPATH', None):
		pythonpath.append(tsk.env.PYTHONPATH)
	if getattr(tg, 'add_to_pythonpath', None):
		pythonpath.append(tg.add_to_pythonpath)
	if pythonpath:
		tsk.env.env['PYTHONPATH'] = os.pathsep.join(pythonpath)

	# dependencies (if the attribute 'deps' changes, trigger a recompilation)
	for x in tg.to_list(getattr(tg, 'deps', [])):
		node = tg.path.find_resource(x)
		if not node:
			tg.bld.fatal(
				'Could not find dependency %r for running %r'
				% (x, src_node.nice_path())
			)
		tsk.dep_nodes.append(node)
	Logs.debug(
		'deps: found dependencies %r for running %r' % (
			tsk.dep_nodes, src_node.nice_path()
		)
	)

	# Bypass the execution of process_source by setting the source to an empty list
	tg.source = []
