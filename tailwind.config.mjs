/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#0c1210',
          900: '#121a17',
          800: '#1a2621',
          700: '#243330',
          600: '#3a4f48',
          500: '#5c736a',
          400: '#8a9e94',
          300: '#b5c4bc',
          200: '#d6e0db',
          100: '#e8efeB',
          50: '#f3f7f5',
        },
        savanna: {
          600: '#b45309',
          500: '#d97706',
          400: '#f59e0b',
          300: '#fbbf24',
        },
        canopy: {
          700: '#14532d',
          600: '#166534',
          500: '#15803d',
          400: '#22c55e',
        },
      },
      fontFamily: {
        display: ['"Fraunces"', 'Georgia', 'serif'],
        sans: ['"DM Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 8px 30px rgba(12, 18, 16, 0.08)',
      },
    },
  },
  plugins: [],
};
