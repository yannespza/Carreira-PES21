// Caricatura do técnico (feita a partir das fotos do usuário): cabelo castanho cacheado, barba cheia,
// olhos castanhos, brinco na orelha esquerda, braços cruzados na mesa da coletiva.
// tom: 'feliz' | 'neutro' | 'irritado'; cor: cor do clube (agasalho)
function tecnicoSVG(tom, cor, cor2){
  cor = cor || '#1f6b3a'; cor2 = cor2 || '#ffffff';
  const pele='#eab995', peleS='#d79c77', cabelo='#3a2416', cabeloL='#5a3a22', barba='#2a1b12';
  // expressões
  const E={
    feliz:{
      sob:`<path d="M152 120 q22 -14 42 -4" stroke="${cabelo}" stroke-width="7" fill="none" stroke-linecap="round"/>
           <path d="M218 116 q20 -10 42 4" stroke="${cabelo}" stroke-width="7" fill="none" stroke-linecap="round"/>`,
      olho:(x)=>`<path d="M${x-15} 142 q15 -13 30 0" stroke="#2a1b12" stroke-width="5" fill="none" stroke-linecap="round"/>`,
      boca:`<path d="M180 196 q26 30 54 0 q-27 12 -54 0z" fill="#fff" stroke="#6b2a22" stroke-width="3" stroke-linejoin="round"/>`,
      extra:`<ellipse cx="160" cy="172" rx="13" ry="7" fill="#f08e7f" opacity=".45"/><ellipse cx="252" cy="172" rx="13" ry="7" fill="#f08e7f" opacity=".45"/>`
    },
    neutro:{
      sob:`<path d="M150 124 q22 -9 44 -3" stroke="${cabelo}" stroke-width="7" fill="none" stroke-linecap="round"/>
           <path d="M218 121 q22 -6 44 3" stroke="${cabelo}" stroke-width="7" fill="none" stroke-linecap="round"/>`,
      olho:(x)=>`<ellipse cx="${x}" cy="143" rx="11" ry="9" fill="#fff"/><circle cx="${x+1}" cy="144" r="6" fill="#5a3a22"/><circle cx="${x+1}" cy="144" r="3" fill="#120c08"/><circle cx="${x+3}" cy="141" r="1.6" fill="#fff"/>
           <path d="M${x-12} 139 q12 -6 24 0" stroke="${peleS}" stroke-width="3" fill="none"/>`,
      boca:`<path d="M186 200 q20 4 40 -1" stroke="#6b2a22" stroke-width="4" fill="none" stroke-linecap="round"/>`,
      extra:''
    },
    irritado:{
      sob:`<path d="M150 116 l46 16" stroke="${cabelo}" stroke-width="8" fill="none" stroke-linecap="round"/>
           <path d="M262 116 l-46 16" stroke="${cabelo}" stroke-width="8" fill="none" stroke-linecap="round"/>
           <path d="M200 112 l4 10 M208 110 l1 11" stroke="${peleS}" stroke-width="2.5" fill="none" stroke-linecap="round"/>`,
      olho:(x)=>`<ellipse cx="${x}" cy="146" rx="11" ry="7" fill="#fff"/><circle cx="${x}" cy="147" r="5.5" fill="#5a3a22"/><circle cx="${x}" cy="147" r="2.6" fill="#120c08"/>`,
      boca:`<path d="M184 206 q22 -18 46 0 q-23 -4 -46 0z" fill="#5a1d17" stroke="#5a1d17" stroke-width="3" stroke-linejoin="round"/>`,
      extra:`<ellipse cx="160" cy="170" rx="14" ry="8" fill="#e0574a" opacity=".35"/><ellipse cx="252" cy="170" rx="14" ry="8" fill="#e0574a" opacity=".35"/>
             <path d="M278 92 l10 -4 l-4 10 l10 -4" stroke="#e0574a" stroke-width="3" fill="none" stroke-linecap="round"/>`
    }
  }[tom] || null;
  const X = E || {sob:'',olho:()=>'',boca:'',extra:''};
  // cachos do cabelo: círculos em volta do topo da cabeça
  const cachos=[[148,96,22],[168,74,27],[198,62,30],[230,64,29],[256,78,26],[268,100,20],[140,112,13],[274,114,13],[186,80,20],[216,78,22],[244,90,18],[160,90,20]]
    .map(([x,y,r])=>`<circle cx="${x}" cy="${y}" r="${r}" fill="${cabelo}" stroke="#1d120a" stroke-width="2"/>`).join('')
    + [[170,68],[200,58],[232,64],[256,84],[150,84],[186,74],[218,72]].map(([x,y])=>`<path d="M${x-8} ${y+4} q8 -10 16 0" stroke="${cabeloL}" stroke-width="3" fill="none" stroke-linecap="round"/>`).join('');
  return `<svg viewBox="0 -34 412 364" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;display:block">
  <!-- corpo: agasalho do clube -->
  <path d="M58 330 q6 -116 92 -136 l56 -8 l56 8 q86 20 92 136z" fill="${cor}" stroke="#0008" stroke-width="2"/>
  <path d="M154 192 l52 44 l52 -44 l-14 -6 l-38 32 l-38 -32z" fill="${cor2}" opacity=".9"/>
  <path d="M206 236 v94" stroke="${cor2}" stroke-width="3" opacity=".8"/>
  <path d="M92 230 q30 -14 46 -10 M320 230 q-30 -14 -46 -10" stroke="#0004" stroke-width="3" fill="none"/>
  <path d="M104 250 q-10 30 -12 80 M308 250 q10 30 12 80" stroke="${cor2}" stroke-width="5" fill="none" opacity=".55"/>
  <g transform="translate(0,-26)">
  <!-- pescoço -->
  <path d="M180 196 h52 v24 q-26 16 -52 0z" fill="${peleS}"/>
  <!-- orelhas e brinco (orelha esquerda dele = direita da imagem) -->
  <ellipse cx="136" cy="152" rx="13" ry="19" fill="${pele}" stroke="#2a1a10" stroke-width="2.5"/><ellipse cx="276" cy="152" rx="13" ry="19" fill="${pele}" stroke="#2a1a10" stroke-width="2.5"/>
  <ellipse cx="276" cy="154" rx="6" ry="10" fill="${peleS}"/>
  <circle cx="281" cy="171" r="5" fill="none" stroke="#c9cdd3" stroke-width="2.6"/>
  <!-- rosto (cabeça grande de caricatura) -->
  <path d="M140 120 q0 -58 66 -58 q66 0 66 58 v42 q0 60 -66 66 q-66 -6 -66 -66z" fill="${pele}" stroke="#2a1a10" stroke-width="3"/>
  <path d="M248 96 q24 20 22 66 q-2 30 -18 46 q14 -34 4 -80z" fill="${peleS}" opacity=".55"/>
  <!-- barba cheia -->
  <path d="M142 160 q4 50 30 66 q34 20 68 0 q26 -16 30 -66 q-8 22 -22 26 q-14 -16 -42 -16 q-28 0 -42 16 q-14 -4 -22 -26z" fill="${barba}" stroke="#140c07" stroke-width="2.5"/>
  ${[[160,200],[172,212],[190,220],[222,220],[240,212],[252,200],[204,224],[166,188],[246,188]].map(([x,y])=>`<path d="M${x} ${y} l3 5" stroke="#4a3322" stroke-width="2"/>`).join('')}
  <path d="M176 186 q30 -14 60 0 q-6 -12 -30 -12 q-24 0 -30 12z" fill="${barba}"/>
  ${X.boca}
  <!-- nariz -->
  <path d="M204 146 q-8 22 -2 30 q8 4 14 -1" stroke="${peleS}" stroke-width="4" fill="none" stroke-linecap="round"/>
  ${X.olho(178)}${X.olho(236)}
  ${X.sob}
  ${X.extra}
  ${cachos}
  </g>
  <!-- mesa da coletiva -->
  <rect x="0" y="262" width="412" height="68" fill="#141821"/>
  <rect x="0" y="258" width="412" height="8" fill="#252b37"/>
  <!-- braços cruzados sobre a mesa -->
  <path d="M100 262 q30 -26 110 -18 q60 6 96 18z" fill="${cor}" stroke="#0006" stroke-width="2"/>
  <path d="M130 262 q50 -20 150 -4" stroke="${cor2}" stroke-width="3" fill="none" opacity=".5"/>
  <ellipse cx="300" cy="256" rx="20" ry="11" fill="${pele}"/><ellipse cx="112" cy="257" rx="19" ry="10" fill="${pele}"/>
  <!-- microfones -->
  <g transform="translate(-58,14)"><rect x="150" y="218" width="5" height="34" fill="#2b2f36"/><rect x="141" y="200" width="23" height="22" rx="10" fill="#3a3f48"/><rect x="138" y="222" width="29" height="14" fill="#e23b3b"/><text x="152.5" y="232" font-size="8" fill="#fff" text-anchor="middle" font-family="Arial" font-weight="700">TV</text></g>
  <g transform="translate(18,14)"><rect x="258" y="222" width="5" height="30" fill="#2b2f36"/><rect x="249" y="204" width="23" height="22" rx="10" fill="#3a3f48"/><rect x="246" y="226" width="29" height="14" fill="#2b6fd6"/><text x="260.5" y="236" font-size="7" fill="#fff" text-anchor="middle" font-family="Arial" font-weight="700">RÁDIO</text></g>
  <!-- garrafa de água -->
  <rect x="360" y="214" width="20" height="46" rx="5" fill="#9fd3ff" opacity=".55"/><rect x="363" y="206" width="14" height="10" fill="#e7eef7"/>
  <!-- plaquinha -->
  <path d="M168 300 h76 l8 -24 h-92z" fill="#e9ecf1"/><text x="206" y="294" font-size="11" fill="#151a22" text-anchor="middle" font-family="Arial" font-weight="700" letter-spacing="1">TÉCNICO</text>
</svg>`;
}
