import typescript from '@rollup/plugin-typescript';
import commonjs from '@rollup/plugin-commonjs';
import resolve from '@rollup/plugin-node-resolve';
import terser from '@rollup/plugin-terser';
import json from '@rollup/plugin-json';
import postcss from 'rollup-plugin-postcss';
import serve from 'rollup-plugin-serve';

const dev = process.env.ROLLUP_WATCH;

export default {
  input: 'src/zoneminder-card.ts',
  output: {
    file: 'dist/zoneminder-card.js',
    format: 'es',
    sourcemap: dev ? true : false,
  },
  plugins: [
    resolve(),
    commonjs(),
    postcss({
      inject: false,  // Don't inject into head, we'll handle it in the component
      minimize: !dev,
    }),
    typescript({
      declaration: false,
    }),
    json(),
    !dev && terser(),
    dev &&
      serve({
        contentBase: ['./dist'],
        host: '0.0.0.0',
        port: 5000,
        allowCrossOrigin: true,
        headers: {
          'Access-Control-Allow-Origin': '*',
        },
      }),
  ].filter(Boolean),
};
