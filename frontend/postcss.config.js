// Tailwind CSS 4 uses the dedicated PostCSS plugin (@tailwindcss/postcss).
// Autoprefixer is retained for the spec; v4 already ships vendor prefixing.
module.exports = {
  plugins: {
    "@tailwindcss/postcss": {},
    autoprefixer: {},
  },
};
